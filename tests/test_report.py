from ai_disclosure.config import Checkbox, Project
from ai_disclosure.gitlog import Commit
from ai_disclosure.report import build_report, checkbox_state

AI = Checkbox("ai", "AI-generated", ("generated with an ai tool",), "2026-11-04")
HUMAN = Checkbox("human", "Read and tested", ("read, understood and tested",), "2026-11-04")
PROJECT = Project(
    slug="demo", name="Demo", repository="demo/demo", trailer_since="2026-11-04", checkboxes=(AI, HUMAN)
)
CLAUDE = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"


def commit(sha, name, email, date, message):
    return Commit(sha, name, email, date + "T10:00:00+01:00", message)


def pull(number, body, messages, login="ada"):
    return {
        "number": number, "title": f"PR {number}", "url": f"https://example.org/{number}",
        "state": "MERGED", "isDraft": False, "createdAt": "2026-11-10T08:00:00Z", "body": body,
        "author": {"login": login, "__typename": "User"},
        "commits": {
            "totalCount": len(messages),
            "nodes": [
                {"commit": {"oid": str(i), "message": m, "author": {"name": "Ada", "email": "ada@example.org", "user": {"login": login}}}}
                for i, m in enumerate(messages)
            ],
        },
    }


def test_checkbox_states():
    body = "- [x] Was a significant part of it generated with an AI tool? Yes\n- [ ] I have read, understood and tested every change."
    assert checkbox_state(body, AI) == "ticked"
    assert checkbox_state(body, HUMAN) == "unticked"
    assert checkbox_state("No template here", AI) == "missing"


def test_commits_are_credited_to_people():
    commits = [
        commit("a", "Ada", "ada@example.org", "2026-10-01", "one"),
        commit("b", "Ada", "ada@example.org", "2026-11-05", "two" + CLAUDE),
        commit("c", "Ada", "ada@home.example", "2026-11-06", "three"),
        # An agent authored it for Ada: credited to her, with the agent as the model.
        commit("d", "copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com", "2026-11-07",
               "four\n\nCo-authored-by: Ada <ada@example.org>\n"),
        commit("e", "dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com", "2026-11-07", "bump"),
        commit("f", "Bob", "bob@example.org", "2026-11-08", "five"),
    ]
    logins = {"a": "ada", "b": "ada", "f": "bob"}
    report = build_report(PROJECT, commits, logins, None)

    ada, bob = report["contributors"]
    assert (ada["login"], ada["commits"], ada["ai_commits"]) == ("ada", 4, 2)
    assert (ada["since_commits"], ada["since_ai_commits"]) == (3, 2)
    assert ada["families"] == {"Claude Opus": 1, "GitHub Copilot": 1}
    assert (bob["commits"], bob["ai_commits"]) == (1, 0)
    assert [other["kind"] for other in report["others"]] == ["bot"]
    assert report["totals"]["humans"] == 2
    assert "example.org" not in str(report)  # no e-mail address is published


def test_pull_requests_are_compared_with_their_commits():
    ticked = "- [x] Was a significant part of it generated with an AI tool?\n- [x] I have read, understood and tested every change"
    unticked = ticked.replace("[x]", "[ ]")
    pulls = [
        pull(1, ticked, ["a" + CLAUDE]),
        pull(2, ticked, ["a"]),
        pull(3, unticked, ["a" + CLAUDE]),
        pull(4, unticked, ["a"]),
        pull(5, "free text", ["a"]),
    ]
    report = build_report(PROJECT, [], {}, pulls)
    assert [item["disclosure"] for item in report["pulls"]["items"]] == [
        "consistent-ai", "box-without-trailer", "trailer-without-box", "consistent-none", "template-missing",
    ]
    assert report["pulls"]["items"][0]["boxes"] == {"ai": "ticked", "human": "ticked"}

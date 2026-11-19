from ai_disclosure.config import Project
from ai_disclosure.gitlog import Commit
from ai_disclosure.report import build_report
from ai_disclosure.stats import build_stats

OPUS = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
SONNET = "\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\n"


def commit(sha, name, email, date, message):
    return Commit(sha, name, email, date + "T10:00:00+01:00", message)


def reports():
    one = [
        commit("a", "Ada", "ada@example.org", "2026-08-01", "one"),
        commit("b", "Ada", "ada@example.org", "2026-08-05", "two" + OPUS),
        # Two models: one commit, under the first model named.
        commit("c", "Ada", "ada@example.org", "2026-10-06", "three" + OPUS + SONNET.strip() + "\n"),
    ]
    two = [
        commit("d", "Ada", "ada@home.example", "2026-11-02", "four" + SONNET),
        commit("e", "Bob", "bob@example.org", "2026-11-03", "five" + SONNET),
        commit("f", "Eve", "eve@example.org", "2026-11-04", "six"),
        # A tool that does not say which model it runs on: counted, but not as a model.
        commit("g", "copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com", "2026-11-04",
               "seven\n\nCo-authored-by: Bob <bob@example.org>\n"),
    ]
    return [
        build_report(Project(slug="one", name="One", repository="demo/one"), one,
                     {"a": "ada", "b": "ada", "c": "ada"}, None, {"b": [10, 0], "c": [5, 5]}),
        build_report(Project(slug="two", name="Two", repository="demo/two"), two,
                     {"d": "ada", "e": "bob"}, None, {"d": [1, 0], "e": [2, 0], "f": [900, 0], "g": [7, 0]}),
    ]


def test_projects_are_added_up():
    stats = build_stats(reports())
    totals = stats["totals"]
    assert (totals["commits"], totals["several"], totals["lines"]) == (5, 1, 30)
    assert totals["people"] == 2  # Ada has two addresses and two projects: one person
    assert (totals["models"], totals["families"], totals["vendors"], totals["tools"]) == (2, 2, 1, 1)
    assert (totals["first"], totals["last"]) == ("2026-08-05", "2026-11-04")
    assert stats["families"] == [
        {"id": "Claude Opus", "vendor": "Anthropic", "commits": 2, "tool": False},
        {"id": "Claude Sonnet", "vendor": "Anthropic", "commits": 2, "tool": False},
        {"id": "GitHub Copilot", "vendor": "GitHub", "commits": 1, "tool": True},
    ]
    # Every month is there, also the one where no commit names a model.
    assert [(month["month"], month["families"]) for month in stats["months"]] == [
        ("2026-08", {"Claude Opus": 1}), ("2026-09", {}), ("2026-10", {"Claude Opus": 1}),
        ("2026-11", {"Claude Sonnet": 2, "GitHub Copilot": 1}),
    ]
    # The list of the models counts a commit for every model it names.
    assert [(model["label"], model["family"], model["commits"], model["first"], model["last"])
            for model in stats["models"]] == [
        ("Claude Sonnet 5.5", "Claude Sonnet", 3, "2026-10-06", "2026-11-03"),
        ("Claude Opus 5.5", "Claude Opus", 2, "2026-08-05", "2026-10-06"),
        ("GitHub Copilot", "GitHub Copilot", 1, "2026-11-04", "2026-11-04"),
    ]
    assert [model["tool"] for model in stats["models"]] == [False, False, True]
    assert stats["vendors"] == [
        {"name": "Anthropic", "commits": 4, "models": 2, "tools": 0},
        {"name": "GitHub", "commits": 1, "models": 0, "tools": 1},
    ]


def test_no_project_and_no_person_is_named():
    text = str(build_stats(reports()))
    for word in ("demo/", "Ada", "ada", "Bob", "example"):
        assert word not in text


def test_nothing_named_and_no_github():
    report = build_report(Project(slug="one", name="One", repository="demo/one"),
                          [commit("a", "Ada", "ada@example.org", "2026-08-01", "one")], None, None)
    stats = build_stats([report])
    assert stats["totals"]["commits"] == 0
    assert stats["totals"]["lines"] is None
    assert stats["months"] == [] and stats["models"] == []

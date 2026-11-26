from xml.etree import ElementTree

from ai_disclosure.badge import STYLE, badge, message, policy_badge, policy_message


def report(since="", **totals):
    base = {"commits": 0, "human_commits": 0, "ai_commits": 0, "since_commits": 0, "since_ai_commits": 0}
    return {"project": {"trailer_since": since}, "totals": {**base, **totals}}


def test_the_badge_says_what_the_page_says():
    assert message(report("2026-11-04", since_commits=180, since_ai_commits=120)) == (
        "declared in 67% of commits since 4 Nov 2026"
    )
    assert message(report(human_commits=23173, ai_commits=1112)) == "declared in 5% of commits"
    assert message(report(human_commits=3496, ai_commits=3)) == "declared in <1% of commits"
    # A rule that no commit has followed yet, and a project with no commit.
    assert message(report("2026-11-18")) == "declared since 18 Nov 2026"
    assert message(report()) == "no commit yet"


def test_the_badge_is_an_image():
    image = ElementTree.fromstring(badge(report(human_commits=10, ai_commits=0)))
    assert image.tag.endswith("svg")
    assert image.get("aria-label") == "AI use: declared in 0% of commits"
    # It carries its dark colours, for a reader whose system is dark.
    assert "prefers-color-scheme:dark" in badge(report(human_commits=10))
    assert "<1%" not in badge(report(human_commits=3496, ai_commits=3))  # escaped


def stated(**fields):
    base = {"readable": True, "file": "ai-policy.yaml", "summary": None, "status": None, "stance": None, "disclosure": None}
    return {**base, **fields}


def test_the_policy_badge_says_what_the_file_states():
    assert policy_message(stated(stance="generated", disclosure="required")) == "generated code accepted · declare it"
    assert policy_message(stated(stance="assisted", disclosure="encouraged")) == "assistance accepted · declaring encouraged"
    assert policy_message(stated(stance="disallowed")) == "AI contributions not accepted"
    assert policy_message(stated(stance="generated", disclosure="none")) == "generated code accepted"
    assert policy_message(stated(disclosure="prohibited")) == "leave AI notes out"
    assert policy_message(stated(summary="neutral", stance="generated")) == "ordinary rules apply"
    assert policy_message(stated(stance="assisted", status="draft")) == "assistance accepted (draft)"
    assert policy_message(stated(stance="assisted", status="adopted")) == "assistance accepted"
    assert policy_message(stated()) == "no rule for code stated"


def test_the_policy_badge_is_written_without_a_file():
    # An image a README shows keeps saying what is true when the file goes away.
    assert policy_message(None) == "no ai-policy.yaml found"
    assert policy_message({"readable": False, "file": ".well-known/ai-policy.yml"}) == (
        ".well-known/ai-policy.yml not understood"
    )
    image = ElementTree.fromstring(policy_badge(stated(stance="generated", disclosure="required")))
    assert image.get("aria-label") == "AI policy: generated code accepted · declare it"
    # The same colours as the other badge, whatever the policy says.
    assert STYLE in policy_badge(stated(stance="disallowed"))

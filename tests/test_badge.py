from xml.etree import ElementTree

from ai_disclosure.badge import badge, message


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
    assert "<1%" not in badge(report(human_commits=3496, ai_commits=3))  # escaped

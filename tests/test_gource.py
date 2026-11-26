from saywhichai.config import Project
from saywhichai.gitlog import Commit
from saywhichai.gource import build_story, disc

PROJECT = Project(slug="demo", name="Demo", repository="example/demo", trailer_since="2026-01-02")


def commit(sha, name, email, date, message):
    return Commit(sha, name, email, date, message)


COMMITS = [
    commit("a", "Ada", "ada@example.org", "2026-01-03T10:00:00+00:00", "second, by date"),
    commit(
        "b", "Ada", "ada@example.org", "2026-01-01T10:00:00+00:00",
        "first\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>",
    ),
    commit("c", "dependabot[bot]", "bot@example.org", "2026-01-04T10:00:00+00:00", "bump"),
]
CHANGES = {"a": [("M", "README.md")], "b": [("A", "README.md"), ("A", "odd|name.txt")], "c": [("M", "lock")]}


def test_a_model_works_beside_the_person():
    story = build_story(PROJECT, COMMITS, CHANGES)
    users = [line.split("|")[1] for line in story.log]
    assert users == ["Ada", "Claude Opus", "Ada"]
    assert story.models == {"Claude Opus": "3987e5"}
    assert story.people == {"Ada": ""}


def test_the_log_follows_time_and_leaves_bots_out():
    story = build_story(PROJECT, COMMITS, CHANGES)
    stamps = [int(line.split("|")[0]) for line in story.log]
    assert stamps == sorted(stamps)
    assert story.commits == 2
    assert not any("lock" in line or "odd" in line for line in story.log)


def test_a_file_has_no_colour_of_its_own():
    # Four fields: time, user, action, path. A fifth one would colour the file.
    story = build_story(PROJECT, COMMITS, CHANGES)
    assert all(len(line.split("|")) == 4 for line in story.log)


def test_captions_and_no_email():
    story = build_story(PROJECT, COMMITS, CHANGES)
    texts = [caption.split("|", 1)[1] for caption in story.captions]
    assert "First commit naming Claude Opus" in texts
    assert "The project asks for a trailer naming the model" in texts
    assert any(text.endswith("2 commits, 50% naming a model") for text in texts)
    assert "@" not in "".join(story.log + story.captions)


def test_disc_is_a_png():
    assert disc("3987e5", 16).startswith(b"\x89PNG\r\n\x1a\n")

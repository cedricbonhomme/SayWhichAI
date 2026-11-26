import subprocess

from saywhichai.gitlog import read_commits, read_releases


def git(repository, *args, date="2026-11-01T10:00:00"):
    env = {
        "GIT_AUTHOR_NAME": "Ada", "GIT_AUTHOR_EMAIL": "ada@example.org", "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": "Ada", "GIT_COMMITTER_EMAIL": "ada@example.org", "GIT_COMMITTER_DATE": date,
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "PATH": "/usr/bin:/bin",
    }
    subprocess.run(["git", *args], cwd=repository, check=True, capture_output=True, env=env)


def test_a_commit_belongs_to_the_first_release_that_holds_it(tmp_path):
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    for number, day in enumerate(("01", "02", "03", "04"), start=1):
        git(tmp_path, "commit", "--allow-empty", "-m", f"commit {number}", date=f"2026-11-{day}T10:00:00")
        if number == 2:
            git(tmp_path, "tag", "v1.0", date="2026-11-02T11:00:00")
        if number == 3:
            # A second tag on the same commit, made later: it holds nothing new.
            git(tmp_path, "tag", "-a", "v1.1", "-m", "1.1", date="2026-11-03T11:00:00")
            git(tmp_path, "tag", "-a", "latest", "-m", "latest", date="2026-11-03T12:00:00")
    shas = [found.sha for found in read_commits(tmp_path)]
    releases = read_releases(tmp_path)
    assert [(release.name, release.date) for release in releases] == [
        ("v1.0", "2026-11-02"), ("v1.1", "2026-11-03"), ("latest", "2026-11-03"),
    ]
    assert [release.commits for release in releases] == [frozenset(shas[:2]), frozenset({shas[2]}), frozenset()]


def test_a_repository_without_a_tag(tmp_path):
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    git(tmp_path, "commit", "--allow-empty", "-m", "commit")
    assert read_releases(tmp_path) == []

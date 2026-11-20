"""Command line: build the site of every project file."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from importlib import resources
from pathlib import Path

from . import __version__
from .config import ConfigError, load_projects
from .github import GitHub, GitHubError, find_token
from .logo import publishable
from .gitlog import mirror, read_changes, read_commits, read_file, read_releases
from .gource import build_story, render, write_story
from .badge import badge
from .report import build_report, recent_months
from .stats import build_stats

DEFAULT_SITE = Path("site.toml")
SITE_HELP = "the file listing the projects to publish (default: site.toml if it exists, else every project)"


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _site_file(args: argparse.Namespace) -> Path | None:
    """The site file asked for, else site.toml when there is one, else none: every project."""
    if args.site:
        if not args.site.is_file():
            raise ConfigError(f"{args.site}: no such site file")
        return args.site
    return DEFAULT_SITE if DEFAULT_SITE.is_file() else None


def build(args: argparse.Namespace) -> int:
    projects = load_projects(args.projects, _site_file(args))
    local = dict(item.split("=", 1) for item in args.local)
    unknown = set(local) - {project.slug for project in projects}
    if unknown:
        raise ConfigError(f"--local names no project file: {', '.join(sorted(unknown))}")

    token = "" if args.no_github else find_token()
    github = GitHub(token) if token else None
    if not github:
        _log("No GitHub token: GitHub accounts and pull requests are left out.")

    output: Path = args.output
    data = output / "data"
    data.mkdir(parents=True, exist_ok=True)
    site = resources.files("ai_disclosure") / "site"
    for entry in site.iterdir():
        if entry.is_file():
            # Not a path when the package is installed as an archive: copy the content.
            (output / entry.name).write_bytes(entry.read_bytes())

    index = []
    reports = []
    for project in projects:
        _log(f"{project.name}: reading the history of {project.repository}")
        repository = Path(local[project.slug]) if project.slug in local else mirror(project, args.cache)
        commits = read_commits(repository, project.branch)

        logins = lines = pulls = None
        logo = ""
        if github:
            branch = project.branch or "HEAD"
            _log(f"{project.name}: asking GitHub for accounts and pull requests")
            known = {}
            for kind in ("accounts", "lines"):
                path = args.cache / f"{project.slug}-{kind}.json"
                known[kind] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            logins, lines = github.commit_facts(project.repository, branch, known["accounts"], known["lines"])
            args.cache.mkdir(parents=True, exist_ok=True)
            (args.cache / f"{project.slug}-accounts.json").write_text(json.dumps(logins), encoding="utf-8")
            (args.cache / f"{project.slug}-lines.json").write_text(
                json.dumps(lines, separators=(",", ":")), encoding="utf-8"
            )
            owner = github.logo(project.repository)
            logo = f"https://github.com/{owner}.png?size=80" if owner else ""
            since = min((box.since for box in project.checkboxes if box.since), default="")
            if since:
                pulls = github.pull_requests(project.repository, since)

        if project.logo:
            # The project file names its own logo: an image of the repository, copied to the site.
            image = read_file(repository, project.logo, project.branch)
            if publishable(project.logo, image):
                name = f"{project.slug}{Path(project.logo).suffix.lower()}"
                (output / "logo").mkdir(exist_ok=True)
                (output / "logo" / name).write_bytes(image)
                logo = f"logo/{name}"
            else:
                _log(f"{project.name}: the logo {project.logo} was not found, is over 512 kB, "
                    "or is an SVG file that holds more than a drawing: skipped"
                )

        releases = read_releases(repository, project.branch)
        report = build_report(project, commits, logins, pulls, lines, releases)
        reports.append(report)
        # A video rendered earlier by "ai-disclosure video" is published with the page.
        video = args.cache / "video" / f"{project.slug}.mp4"
        if video.exists():
            (output / "video").mkdir(exist_ok=True)
            shutil.copyfile(video, output / "video" / video.name)
            report["video"] = {"file": f"video/{video.name}", "poster": ""}
            if video.with_suffix(".jpg").exists():
                shutil.copyfile(video.with_suffix(".jpg"), output / "video" / f"{project.slug}.jpg")
                report["video"]["poster"] = f"video/{project.slug}.jpg"
        (data / f"{project.slug}.json").write_text(
            json.dumps(report, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        (output / "badge").mkdir(exist_ok=True)
        (output / "badge" / f"{project.slug}.svg").write_text(badge(report), encoding="utf-8")
        totals = report["totals"]
        index.append(
            {
                "slug": project.slug,
                "name": project.name,
                "repository": project.repository,
                "logo": logo,
                "trailer_since": project.trailer_since,
                "totals": totals,
                "recent": recent_months(report),
            }
        )
        _log(
            f"{project.name}: {totals['commits']} commits, {totals['ai_commits']} declaring a model, "
            f"{totals['humans']} people, {len((report['pulls'] or {}).get('items', []))} pull requests"
        )

    (data / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (data / "stats.json").write_text(
        json.dumps(build_stats(reports), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    _log(f"Site written to {output}/")
    return 0


def video(args: argparse.Namespace) -> int:
    projects = load_projects(args.projects, _site_file(args))
    local = dict(item.split("=", 1) for item in args.local)
    unknown = (set(local) | set(args.slug)) - {project.slug for project in projects}
    if unknown:
        raise ConfigError(f"no project file is named: {', '.join(sorted(unknown))}")

    def recent(project) -> bool:
        output = args.cache / "video" / f"{project.slug}.mp4"
        return output.exists() and time.time() - output.stat().st_mtime < args.max_age * 86400

    if args.due:
        # Only say which videos would be rendered: gource and ffmpeg are not needed.
        for project in projects:
            if (not args.slug or project.slug in args.slug) and not recent(project):
                print(project.slug)
        return 0
    missing = [tool for tool in (os.environ.get("GOURCE", "gource"), "ffmpeg") if not shutil.which(tool)]
    if missing:
        raise ConfigError(f"not installed: {', '.join(missing)}")

    failed = False
    for project in projects:
        if args.slug and project.slug not in args.slug:
            continue
        output = args.cache / "video" / f"{project.slug}.mp4"
        if recent(project):
            _log(f"{project.name}: the video is recent enough, kept")
            continue
        _log(f"{project.name}: reading the history of {project.repository}")
        repository = Path(local[project.slug]) if project.slug in local else mirror(project, args.cache)
        commits = read_commits(repository, project.branch)
        changes = read_changes(repository, project.branch)
        # The accounts found by an earlier "build": no call to the GitHub API here.
        known = args.cache / f"{project.slug}-accounts.json"
        logins = json.loads(known.read_text(encoding="utf-8")) if known.exists() else {}
        story = build_story(project, commits, changes, logins)
        if not story.log:
            _log(f"{project.name}: no commit to show")
            continue
        with tempfile.TemporaryDirectory() as work:
            write_story(story, Path(work), None if args.no_github else args.cache / "avatars")
            _log(f"{project.name}: rendering {story.seconds} seconds of video at most")
            started = time.time()
            try:
                render(story, Path(work), project.name, output, args.size)
            except subprocess.CalledProcessError as error:
                # One project must not keep the others from having their video.
                _log(f"{project.name}: no video, {error.cmd[0]} failed. {(error.stderr or '').strip()}")
                failed = True
                continue
        _log(f"{project.name}: {output} written in {round(time.time() - started)} s")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-disclosure", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("build", help="read the projects and write the static site")
    command.add_argument("--projects", type=Path, default=Path("projects"), help="directory of project files")
    command.add_argument("--output", type=Path, default=Path("_site"), help="where to write the site")
    command.add_argument("--cache", type=Path, default=Path(".cache"), help="where the clones are kept")
    command.add_argument("--site", type=Path, metavar="FILE", help=SITE_HELP)
    command.add_argument(
        "--local",
        action="append",
        default=[],
        metavar="SLUG=PATH",
        help="read this project from an existing clone instead of cloning it",
    )
    command.add_argument("--no-github", action="store_true", help="do not call the GitHub API")
    command.set_defaults(run=build)

    command = commands.add_parser("video", help="render a Gource video of each project (needs gource and ffmpeg)")
    command.add_argument("slug", nargs="*", help="only these projects (file names without .toml)")
    command.add_argument("--projects", type=Path, default=Path("projects"), help="directory of project files")
    command.add_argument("--cache", type=Path, default=Path(".cache"), help="where clones and videos are kept")
    command.add_argument("--site", type=Path, metavar="FILE", help=SITE_HELP)
    command.add_argument("--local", action="append", default=[], metavar="SLUG=PATH",
                         help="read this project from an existing clone instead of cloning it")
    command.add_argument("--max-age", type=float, default=0, metavar="DAYS",
                         help="keep a video rendered less than this many days ago")
    command.add_argument("--due", action="store_true",
                         help="only print the projects whose video is missing or too old")
    command.add_argument("--size", default="1280x720", help="size of the video")
    command.add_argument("--no-github", action="store_true", help="do not download profile pictures")
    command.set_defaults(run=video)

    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (ConfigError, GitHubError) as error:
        _log(f"error: {error}")
    except subprocess.CalledProcessError as error:
        _log(f"error: {' '.join(error.cmd)} failed: {(error.stderr or '').strip()}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

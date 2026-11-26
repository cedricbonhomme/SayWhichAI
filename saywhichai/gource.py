"""A Gource video of a project's history, with the declared models as users.

Each commit is shown as the work of the person it is credited to. When the commit
names a model, the model family works on the same files beside that person.

Nothing more is claimed: a file keeps the colour of its type whoever changed it,
because a trailer says that a model took part in a commit, not how much of a file
it wrote.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import urllib.error
import urllib.request
import zlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import Project
from .gitlog import Commit
from .report import MAX_FAMILIES, Identities

# The site's series colours on a dark surface, in the same order: a family has the
# same colour in the video and in the charts.
SERIES = ["3987e5", "d95926", "199e70", "c98500", "d55181", "0ca30c", "9085e9", "e66767"]
BACKGROUND = "0d0d0d"
MIN_SECONDS, MAX_SECONDS, COMMITS_PER_SECOND = 60, 180, 200


@dataclass
class Story:
    """What Gource needs to tell the history of a project."""

    log: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    people: dict[str, str] = field(default_factory=dict)  # user name -> GitHub login, or ""
    models: dict[str, str] = field(default_factory=dict)  # model family -> colour
    commits: int = 0
    first: float = 0
    last: float = 0

    @property
    def seconds(self) -> int:
        """Length of the video: longer for a longer history, within limits."""
        return round(min(MAX_SECONDS, max(MIN_SECONDS, MIN_SECONDS + self.commits / COMMITS_PER_SECOND)))

    @property
    def seconds_per_day(self) -> float:
        days = max(1.0, (self.last - self.first) / 86400)
        return self.seconds / days


def _clean(text: str) -> str:
    """Gource separates the fields of its log with a bar."""
    return " ".join(text.replace("|", " ").split())


def build_story(
    project: Project,
    commits: list[Commit],
    changes: dict[str, list[tuple[str, str]]],
    logins: dict[str, str] | None = None,
) -> Story:
    logins = logins or {}
    identities = Identities(project, commits, logins)
    story = Story()
    names: dict[str, str] = {}  # one name per person, the first one seen
    family_commits: Counter = Counter()
    first_seen: dict[str, float] = {}
    years: dict[int, list] = {}  # year -> [commits, commits naming a model, last timestamp]
    entries = []

    for commit in commits:
        credit = identities.credit(
            commit.author_name, commit.author_email, commit.message, logins.get(commit.sha, "")
        )
        if credit.kind == "bot":
            continue
        moment = datetime.fromisoformat(commit.date)
        stamp = moment.timestamp()
        families = list(dict.fromkeys(model.family for model in credit.models))

        year = years.setdefault(moment.astimezone(timezone.utc).year, [0, 0, 0.0])
        year[0] += 1
        year[1] += bool(families)
        year[2] = max(year[2], stamp)
        story.commits += 1
        for family in families:
            family_commits[family] += 1
            first_seen[family] = min(stamp, first_seen.get(family, stamp))

        users = [_clean(family) for family in families]
        if credit.kind == "human":
            name = names.setdefault(credit.key, _clean(credit.name) or "Unknown")
            story.people.setdefault(name, credit.login)
            users.insert(0, name)
        for action, path in changes.get(commit.sha, []):
            if "|" in path:
                continue
            for user in users:
                entries.append((int(stamp), f"{user}|{action}|/{path}"))

    # Gource reads its log in the order of time; author dates do not always follow
    # the order of the history.
    entries.sort(key=lambda entry: entry[0])
    story.log = [f"{stamp}|{line}" for stamp, line in entries]
    if entries:
        story.first, story.last = entries[0][0], entries[-1][0]

    for index, (family, _) in enumerate(family_commits.most_common()):
        story.models[_clean(family)] = SERIES[min(index, MAX_FAMILIES)]

    captions = [(stamp, f"First commit naming {_clean(family)}") for family, stamp in first_seen.items()]
    if project.trailer_since:
        since = datetime.fromisoformat(project.trailer_since).replace(tzinfo=timezone.utc).timestamp()
        if story.first <= since <= story.last:
            captions.append((since, "The project asks for a trailer naming the model"))
    current = datetime.now(timezone.utc).year
    for number, (count, named, last) in sorted(years.items()):
        text = f"{number}{' so far' if number == current else ''}: {count:,} commits"
        if named:
            text += f", {max(1, round(100 * named / count))}% naming a model"
        captions.append((last, text))
    story.captions = [f"{int(stamp)}|{text}" for stamp, text in sorted(captions)]
    return story


def disc(colour: str, size: int = 128) -> bytes:
    """A plain disc as a PNG image: the picture of a model family."""
    red, green, blue = bytes.fromhex(colour)
    centre, radius = (size - 1) / 2, size / 2 - 1
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            cover = radius - math.hypot(x - centre, y - centre) + 0.5
            rows += bytes((red, green, blue, round(255 * min(1.0, max(0.0, cover)))))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows)))
        + chunk(b"IEND", b"")
    )


def _profile_picture(login: str, cache: Path) -> Path | None:
    """The GitHub profile picture of an account as a PNG file, kept between runs."""
    picture = cache / f"{login.lower()}.png"
    if picture.exists():
        return picture
    cache.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f"https://github.com/{login}.png?size=128", headers={"User-Agent": "saywhichai"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError):
        return None
    # GitHub answers with a PNG or a JPEG file whatever the name says.
    source = cache / f"{login.lower()}.download"
    source.write_bytes(raw)
    done = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-frames:v", "1", "-vf", "scale=128:128",
         # Gource stops on a picture that is not in colour.
         "-pix_fmt", "rgba", "-f", "image2", "-vcodec", "png", str(picture)],
        capture_output=True,
    )
    source.unlink()
    if done.returncode:
        picture.unlink(missing_ok=True)
        return None
    return picture


def write_story(story: Story, work: Path, pictures: Path | None) -> None:
    """Write the log, the captions and the pictures of the users to a directory."""
    avatars = work / "avatars"
    avatars.mkdir(parents=True, exist_ok=True)
    (work / "gource.log").write_text("\n".join(story.log) + "\n", encoding="utf-8")
    (work / "captions.txt").write_text("\n".join(story.captions) + "\n", encoding="utf-8")
    for family, colour in story.models.items():
        if "/" not in family:
            (avatars / f"{family}.png").write_bytes(disc(colour))
    if pictures is None:
        return
    for name, login in story.people.items():
        # A person named like a model family keeps the family's disc.
        if not login or "/" in name or name in story.models:
            continue
        picture = _profile_picture(login, pictures)
        if picture:
            shutil.copyfile(picture, avatars / f"{name}.png")


def render(story: Story, work: Path, title: str, output: Path, size: str = "1280x720", fps: int = 30) -> None:
    """Run Gource and ffmpeg. Gource needs a display: a real one, or xvfb-run."""
    gource = [
        os.environ.get("GOURCE", "gource"), str(work / "gource.log"),
        "--log-format", "custom",
        f"-{size}", "--output-framerate", str(fps), "-o", "-",
        "--title", title,
        "--caption-file", str(work / "captions.txt"),
        "--caption-size", "20", "--caption-duration", "3", "--caption-colour", "FFFFFF",
        "--seconds-per-day", f"{story.seconds_per_day:.5f}",
        "--auto-skip-seconds", "0.5", "--max-file-lag", "0.1",
        "--user-image-dir", str(work / "avatars"),
        "--file-idle-time", "0", "--max-files", "0",
        "--hide", "filenames,mouse,progress",
        "--highlight-users", "--user-scale", "1.4",
        "--key", "--date-format", "%B %Y",
        "--font-size", "16",
        "--bloom-multiplier", "1.1", "--bloom-intensity", "0.6",
        "--background-colour", BACKGROUND,
        "--dir-name-depth", "2", "--dir-font-size", "11",
        "--camera-mode", "overview",
        "--stop-at-end",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(f"{output.stem}.part{output.suffix}")
    ffmpeg = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-r", str(fps), "-f", "image2pipe", "-vcodec", "ppm", "-i", "-",
        "-vcodec", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf", "24",
        "-movflags", "+faststart", str(partial),
    ]
    frames = subprocess.Popen(gource, stdout=subprocess.PIPE)
    try:
        encoded = subprocess.run(ffmpeg, stdin=frames.stdout, capture_output=True, text=True)
    finally:
        if frames.stdout:
            frames.stdout.close()
        status = frames.wait()
    if status or encoded.returncode:
        partial.unlink(missing_ok=True)
        failed = gource if status else ffmpeg
        raise subprocess.CalledProcessError(status or encoded.returncode, failed[:1], stderr=encoded.stderr)
    partial.replace(output)
    # The last second of the video, as the picture shown before it plays.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-1", "-i", str(output),
         "-frames:v", "1", "-update", "1", "-q:v", "4", str(output.with_suffix(".jpg"))],
        capture_output=True,
    )

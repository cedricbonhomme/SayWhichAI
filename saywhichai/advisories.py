"""Commits that vulnerability records cite as a reference, from Vulnerability-Lookup.

A record that cites a commit is a firmer sign that the commit fixed a vulnerability
than a label in its subject line, but it is not proof either: a record can cite the
commit that introduced the problem, or one among several.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable

API = "https://vulnerability.circl.lu/api/vulnerability/fulltext"
RECORD_URL = "https://vulnerability.circl.lu/vuln/"
PAGE = 100
MAX_PAGES = 20
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")


class AdvisoryError(RuntimeError):
    pass


def _fetch(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "saywhichai", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt == 2:
                raise AdvisoryError(f"Vulnerability-Lookup unreachable: {error}") from error
            time.sleep(2**attempt)
    raise AdvisoryError("Vulnerability-Lookup: too many failed attempts")


def _commit_re(repository: str) -> re.Pattern:
    owner, name = (re.escape(part) for part in repository.split("/"))
    return re.compile(
        rf"^https?://(?:www\.)?github\.com/{owner}/{name}/(?:pull/\d+/)?commits?/(?P<sha>[0-9a-f]{{7,40}})\b", re.I
    )


def _references(record: dict) -> Iterable[str]:
    """The reference addresses of a CVE record (format 5), from every container."""
    containers = record.get("containers") or {}
    blocks = [containers.get("cna") or {}, *(containers.get("adp") or [])]
    for block in blocks:
        for reference in block.get("references") or []:
            if isinstance(reference, dict) and isinstance(reference.get("url"), str):
                yield reference["url"]


def cited_commits(
    repository: str, sources: Iterable[str] = (), fetch: Callable[[str], dict] = _fetch
) -> dict[str, list[str]]:
    """The commits of the repository that records cite (a full or short id), with the
    ids of the records that cite them.

    The search is a full-text one, ranked by relevance: the reading stops at the first
    page where no record cites the repository.
    """
    pattern = _commit_re(repository)
    cited: dict[str, set[str]] = {}
    for page in range(1, MAX_PAGES + 1):
        query = {"q": f"github.com/{repository}/commit", "page": page, "per_page": PAGE}
        if sources:
            query["sources"] = ",".join(sources)
        records = fetch(f"{API}?{urllib.parse.urlencode(query)}").get("data") or []
        found = False
        for record in records:
            if not isinstance(record, dict):
                continue
            record_id = str((record.get("cveMetadata") or {}).get("cveId") or record.get("id") or "")
            if not ID_RE.match(record_id):
                continue
            for url in _references(record):
                match = pattern.match(url)
                if match:
                    cited.setdefault(match.group("sha").lower(), set()).add(record_id)
                    found = True
        if not found or len(records) < PAGE:
            break
    return {sha: sorted(ids) for sha, ids in sorted(cited.items())}


def resolve(cited: dict[str, list[str]], shas: Iterable[str]) -> dict[str, list[str]]:
    """The cited commits that are in the history, under their full id. A short id that
    matches no commit, or several, is left out."""
    shas = list(shas)
    full = set(shas)
    result: dict[str, set[str]] = {}
    for sha, ids in cited.items():
        if sha in full:
            found = [sha]
        else:
            found = [candidate for candidate in shas if candidate.startswith(sha)]
        if len(found) == 1:
            result.setdefault(found[0], set()).update(ids)
    return {sha: sorted(ids) for sha, ids in result.items()}

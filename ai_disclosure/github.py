"""What git does not know: GitHub accounts and pull requests (GraphQL API)."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"


class GitHubError(RuntimeError):
    pass


def find_token() -> str:
    """GITHUB_TOKEN or GH_TOKEN, else the token of the gh command when it is logged in."""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


class GitHub:
    def __init__(self, token: str):
        self.token = token

    def query(self, query: str, **variables: object) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        request = urllib.request.Request(
            API,
            data=body,
            headers={
                "Authorization": f"bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "ai-disclosure",
            },
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
            except urllib.error.HTTPError as error:
                if error.code in (502, 503, 504) and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise GitHubError(f"GitHub API answered {error.code}: {error.reason}") from error
            except urllib.error.URLError as error:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise GitHubError(f"GitHub API unreachable: {error.reason}") from error
            if payload.get("errors"):
                raise GitHubError("; ".join(e.get("message", "?") for e in payload["errors"]))
            return payload["data"]
        raise GitHubError("GitHub API: too many failed attempts")

    def commit_logins(self, repository: str, ref: str, known: dict[str, str] | None = None) -> dict[str, str]:
        """The GitHub account of the author of each commit, by commit id ("" for none).

        The history is read from the most recent commit, and the reading stops at the
        first page that brings nothing new: with the accounts already known from a
        previous run, only the new commits are asked for.
        """
        owner, name = repository.split("/")
        logins = dict(known or {})
        cursor = None
        while True:
            data = self.query(_COMMITS, owner=owner, name=name, ref=ref, cursor=cursor)
            target = (data["repository"] or {}).get("object")
            if not target:
                raise GitHubError(f"{repository}: branch {ref!r} not found")
            history = target["history"]
            new = 0
            for node in history["nodes"]:
                new += node["oid"] not in logins
                logins[node["oid"]] = ((node["author"] or {}).get("user") or {}).get("login", "")
            if not new or not history["pageInfo"]["hasNextPage"]:
                return logins
            cursor = history["pageInfo"]["endCursor"]

    def pull_requests(self, repository: str, since: str) -> list[dict]:
        """The pull requests opened from the date on, most recent first."""
        owner, name = repository.split("/")
        pulls: list[dict] = []
        cursor = None
        while True:
            data = self.query(_PULLS, owner=owner, name=name, cursor=cursor)
            page = data["repository"]["pullRequests"]
            for node in page["nodes"]:
                if node["createdAt"][:10] < since:
                    return pulls
                pulls.append(node)
            if not page["pageInfo"]["hasNextPage"]:
                return pulls
            cursor = page["pageInfo"]["endCursor"]


_COMMITS = """
query($owner: String!, $name: String!, $ref: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    object(expression: $ref) {
      ... on Commit {
        history(first: 100, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          nodes { oid author { user { login } } }
        }
      }
    }
  }
}
"""

_PULLS = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 30, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title url state isDraft createdAt body
        author { login __typename }
        commits(first: 100) {
          totalCount
          nodes { commit { oid message author { name email user { login } } } }
        }
      }
    }
  }
}
"""

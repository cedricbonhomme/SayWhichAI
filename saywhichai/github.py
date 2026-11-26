"""What git does not know: GitHub accounts and pull requests (GraphQL API)."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

API = "https://api.github.com/graphql"
PAGE = 100


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
                "User-Agent": "saywhichai",
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

    def commit_facts(
        self,
        repository: str,
        ref: str,
        logins: dict[str, str] | None = None,
        lines: dict[str, list[int]] | None = None,
    ) -> tuple[dict[str, str], dict[str, list[int]]]:
        """What GitHub knows of each commit, by commit id: the account of its author
        ("" for none), and the lines it adds and deletes.

        The history is read from the most recent commit, and the reading stops at the
        first page that brings nothing new: with what is already known from a
        previous run, only the new commits are asked for.
        """
        owner, name = repository.split("/")
        logins, lines = dict(logins or {}), dict(lines or {})
        cursor = None
        size = PAGE
        while True:
            try:
                data = self.query(_COMMITS, owner=owner, name=name, ref=ref, cursor=cursor, size=size)
            except GitHubError:
                # Counting the lines of very large commits can take GitHub too long:
                # ask for fewer commits at a time.
                if size <= 10:
                    raise
                size //= 2
                continue
            target = (data["repository"] or {}).get("object")
            if not target:
                raise GitHubError(f"{repository}: branch {ref!r} not found")
            history = target["history"]
            new = 0
            for node in history["nodes"]:
                new += node["oid"] not in logins or node["oid"] not in lines
                logins[node["oid"]] = ((node["author"] or {}).get("user") or {}).get("login", "")
                lines[node["oid"]] = [node["additions"], node["deletions"]]
            if not new or not history["pageInfo"]["hasNextPage"]:
                return logins, lines
            cursor = history["pageInfo"]["endCursor"]
            size = PAGE

    def logo(self, repository: str) -> str:
        """The account whose picture is the logo of the project, or nothing.

        GitHub has no logo for a repository. An organisation has a picture, and it is
        a logo; the picture of a person is their portrait, and is not one.
        """
        owner, name = repository.split("/")
        account = self.query(_OWNER, owner=owner, name=name)["repository"]["owner"]
        return account["login"] if account["__typename"] == "Organization" else ""

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


_OWNER = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) { owner { __typename login } }
}
"""

_COMMITS = """
query($owner: String!, $name: String!, $ref: String!, $cursor: String, $size: Int!) {
  repository(owner: $owner, name: $name) {
    object(expression: $ref) {
      ... on Commit {
        history(first: $size, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          nodes { oid additions deletions author { user { login } } }
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

"""What a project states about AI in its own repository: its ai-policy.yaml file.

The format is the proposal of https://codeberg.org/open-source-ecosystem/ai-policy
(version 1). This module reads the few fields the site shows: the stance on code,
whether and how the use of AI is declared, the contributor's own review and
autonomous agents. A file with an unknown version, or with a value this module does
not know in a field it reads, is not half shown: it is reported as unreadable.
"""

from __future__ import annotations

import posixpath
import re
from urllib.parse import quote

from .yamlsubset import YamlError, load

# Where the file is looked for, in the order of the proposal.
FILES = ("ai-policy.yaml", "ai-policy.yml", ".well-known/ai-policy.yaml", ".well-known/ai-policy.yml")
LIMIT = 64 * 1024

SUMMARY = ("neutral", "permissive", "mixed", "restrictive", "disallowed")
STATUS = ("adopted", "draft", "under-discussion")
STANCE = ("disallowed", "assisted", "generated")
DISCLOSURE = ("prohibited", "none", "encouraged", "required")
HUMAN_REVIEW = ("none", "required")
METHOD = ("free-text", "commit-trailer", "pr-template", "quote-block")
CONTENT = ("tool", "model", "extent", "usage")
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.-]{0,60}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class PolicyError(ValueError):
    pass


def _one(holder: dict, key: str, known: tuple[str, ...]) -> str | None:
    value = holder.get(key)
    if value is None:
        return None
    if value not in known:
        raise PolicyError(f"{key}: {value!r} is not a known value")
    return value


def _many(holder: dict, key: str, known: tuple[str, ...] | None = None) -> list[str]:
    values = holder.get(key)
    if values is None:
        return []
    if not isinstance(values, list):
        raise PolicyError(f"{key}: a list is expected")
    for value in values:
        if not isinstance(value, str) or (known and value not in known) or (not known and not WORD_RE.match(value)):
            raise PolicyError(f"{key}: {value!r} is not a known value")
    return values


def _section(holder: dict, key: str) -> dict:
    value = holder.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PolicyError(f"{key}: a mapping is expected")
    return value


def _text(holder: dict, key: str) -> str:
    value = holder.get(key)
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 300 or any(ord(char) < 32 for char in value):
        raise PolicyError(f"{key}: a short text is expected")
    return value.strip()


def read_policy(text: str) -> dict:
    """The fields the site shows, or PolicyError when the file is not understood."""
    try:
        data = load(text)
    except (YamlError, RecursionError) as error:
        raise PolicyError(str(error)) from error
    if not isinstance(data, dict):
        raise PolicyError("a mapping is expected")
    if data.get("version") != 1 or isinstance(data.get("version"), bool):
        raise PolicyError(f"version {data.get('version')!r} is not understood")

    # The rules for code: the defaults, then what the file says for code alone.
    rules = dict(_section(data, "defaults"))
    scopes = []
    assertions = data.get("assertions") or []
    if not isinstance(assertions, list) or not all(isinstance(entry, dict) for entry in assertions):
        raise PolicyError("assertions: a list of mappings is expected")
    for entry in assertions:
        scope = entry.get("scope")
        if not isinstance(scope, str) or not WORD_RE.match(scope):
            raise PolicyError("assertions: a scope is expected")
        if scope == "code":
            rules.update(entry)
        else:
            scopes.append(scope)

    agents = _section(data, "autonomousAgents").get("allowed")
    exceptions = data.get("exceptions")
    if agents not in (None, True, False) or exceptions not in (None, True, False):
        raise PolicyError("true or false is expected")

    form = _section(data, "disclosureFormat")
    trailers = [_text(form, "trailer")] if form.get("trailer") else []
    named = _section(form, "trailers")
    trailers += [_text(named, key) for key in named]

    return {
        "readable": True,
        "summary": _one(data, "summary", SUMMARY),
        "status": _one(data, "status", STATUS),
        "exceptions": bool(exceptions),
        "undecided": _many(data, "undecided"),
        "statement": _text(data, "statement"),
        "stance": _one(rules, "stance", STANCE),
        "disclosure": _one(rules, "disclosure", DISCLOSURE),
        "human_review": _one(rules, "humanReview", HUMAN_REVIEW),
        "agents": agents,
        "method": _many(form, "method", METHOD),
        "trailers": sorted({trailer.rstrip(":") for trailer in trailers if trailer}),
        "content": _many(form, "content", CONTENT),
        "scopes": sorted(set(scopes)),
    }


def link(base: str, pointer: str) -> str:
    """The address of a pointer of the file: a web address, or a path in the repository.

    base is the address of the root of the repository on its branch. Nothing but
    http and https is kept: the pointer comes from the repository.
    """
    if re.match(r"^https?://[^\s<>\"]+$", pointer):
        return pointer
    if not pointer or SCHEME_RE.match(pointer) or pointer.startswith("//"):
        return ""
    path, _, fragment = pointer.partition("#")
    path = posixpath.normpath("/" + path).lstrip("/")
    return f"{base}/{quote(path)}" + (f"#{quote(fragment)}" if fragment else "")

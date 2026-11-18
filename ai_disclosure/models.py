"""Recognise AI models in Co-Authored-By trailers and give them one name.

The same model is written in several ways ("Claude Opus 4.8",
"Claude Opus 4.8 (1M context)", "Codex (GPT-6)"). A trailer is turned into a
vendor, a family and a version, so that spellings of one model count together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TRAILER_RE = re.compile(
    r"^[ \t]*co-authored-by:[ \t]*(?P<name>[^<\n]*?)[ \t]*(?:<(?P<email>[^>\n]*)>)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

_VERSION = r"(?P<version>\d+(?:\.\d+)*[a-z]?)"


@dataclass(frozen=True)
class Model:
    vendor: str
    family: str
    version: str = ""

    @property
    def label(self) -> str:
        return f"{self.family} {self.version}".strip()


@dataclass(frozen=True)
class CoAuthor:
    name: str
    email: str
    model: Model | None = None


@dataclass(frozen=True)
class Rule:
    """A custom rule from a project file: a substring of the trailer names a model."""

    match: str
    vendor: str
    family: str
    version: str = ""


# Tools that carry a first name (Devin, Jules) are recognised by their e-mail
# address only, so that a person called Devin stays a person.
# (pattern on the name, vendor, family). "{tier}" in a family is replaced by the
# named group, so that Claude Opus and Claude Sonnet are two families.
_NAME_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            rf"\bclaude\b(?:[ -](?P<tier>opus|sonnet|haiku|fable|mythos|instant))?(?:[ -]v?{_VERSION})?",
            re.I,
        ),
        "Anthropic",
        "Claude {tier}",
    ),
    (re.compile(rf"\bgpt[ -]?{_VERSION}(?P<suffix>[a-z-]*)", re.I), "OpenAI", "GPT"),
    (re.compile(rf"\bcodex\b(?:[ -]v?{_VERSION})?", re.I), "OpenAI", "Codex"),
    (re.compile(r"\bchatgpt\b", re.I), "OpenAI", "ChatGPT"),
    (
        re.compile(rf"\bgemini\b(?:[ -]v?{_VERSION})?(?:[ -](?P<tier>pro|flash|ultra))?", re.I),
        "Google",
        "Gemini {tier}",
    ),
    (re.compile(r"\bcopilot\b", re.I), "GitHub", "GitHub Copilot"),
    (re.compile(r"\bcursor ?agent\b", re.I), "Cursor", "Cursor"),
    (re.compile(r"\baider\b", re.I), "Aider", "Aider"),
    (re.compile(r"\bamazon q\b", re.I), "Amazon", "Amazon Q"),
    (re.compile(rf"\b(?:mistral|codestral|devstral)\b(?:[ -]v?{_VERSION})?", re.I), "Mistral AI", "Mistral"),
    (re.compile(rf"\bdeepseek\b(?:[ -]v?{_VERSION})?", re.I), "DeepSeek", "DeepSeek"),
    (re.compile(rf"\bqwen\b(?:[ -]v?{_VERSION})?", re.I), "Alibaba", "Qwen"),
    (re.compile(rf"\bgrok\b(?:[ -]v?{_VERSION})?", re.I), "xAI", "Grok"),
    (re.compile(rf"\bllama\b(?:[ -]v?{_VERSION})?", re.I), "Meta", "Llama"),
]

# When the name says nothing, the e-mail address of the trailer may.
_EMAIL_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"@anthropic\.com$", re.I), "Anthropic", "Claude"),
    (re.compile(r"@openai\.com$", re.I), "OpenAI", "OpenAI"),
    (re.compile(r"copilot@|\+copilot@", re.I), "GitHub", "GitHub Copilot"),
    (re.compile(r"cursoragent@cursor\.com$", re.I), "Cursor", "Cursor"),
    (re.compile(r"@aider\.chat$", re.I), "Aider", "Aider"),
    (re.compile(r"devin-ai-integration", re.I), "Cognition", "Devin"),
    (re.compile(r"google-labs-jules", re.I), "Google", "Jules"),
    (re.compile(r"@windsurf\.com$|@codeium\.com$", re.I), "Windsurf", "Windsurf"),
]


def identify(name: str, email: str = "", rules: list[Rule] | None = None) -> Model | None:
    """Return the model a co-author (or a commit author) stands for, or None for a human."""
    text = f"{name} <{email}>".lower()
    for rule in rules or []:
        if rule.match.lower() in text:
            return Model(rule.vendor, rule.family, rule.version)

    # A specific model named anywhere wins over the tool around it: "Codex (GPT-6)"
    # is GPT 6, and the tool is a detail.
    best: tuple[int, Model] | None = None
    for pattern, vendor, family in _NAME_RULES:
        found = pattern.search(name)
        if not found:
            continue
        groups = found.groupdict()
        tier = (groups.get("tier") or "").capitalize()
        version = groups.get("version") or ""
        model = Model(vendor, " ".join(family.replace("{tier}", tier).split()), version)
        score = (2 if version else 0) + (1 if tier else 0)
        if family.startswith("Claude") and not score and not email.lower().endswith("@anthropic.com"):
            continue  # Claude is also a first name and a surname
        if best is None or score > best[0]:
            best = (score, model)
    if best:
        return best[1]

    for pattern, vendor, family in _EMAIL_RULES:
        if pattern.search(email):
            return Model(vendor, family)
    return None


def co_authors(message: str, rules: list[Rule] | None = None) -> list[CoAuthor]:
    """Every Co-Authored-By line of a commit message, models identified."""
    seen: set[tuple[str, str]] = set()
    result = []
    for found in TRAILER_RE.finditer(message):
        name = found.group("name").strip()
        email = (found.group("email") or "").strip()
        key = (name.lower(), email.lower())
        if key in seen or not (name or email):
            continue
        seen.add(key)
        result.append(CoAuthor(name, email, identify(name, email, rules)))
    return result

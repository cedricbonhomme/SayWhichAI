"""Recognise AI models in commit trailers and give them one name.

The same model is written in several ways ("Claude Opus 4.8",
"Claude Opus 4.8 (1M context)", "Codex (GPT-6)"). A trailer is turned into a
vendor, a family and a version, so that spellings of one model count together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Co-Authored-By names a person or a model. Assisted-by and Generated-by are the
# names other projects give to the same declaration (Mesa, Fedify, the Linux kernel,
# the Apache Software Foundation): they are read too, and only for the models they name.
TRAILER_RE = re.compile(
    r"^[ \t]*(?P<kind>co-authored-by|assisted-by|generated-by):"
    r"[ \t]*(?P<name>[^<\n]*?)[ \t]*(?:<(?P<email>[^>\n]*)>)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

_VERSION = r"(?P<version>\d+(?:\.\d+)*[a-z]?)"


# Tools that run on a model they do not name: an assistant or an agent that works
# with the models of several vendors, or with one that changes over time. A commit
# naming one of them declares the use of AI, and leaves the model unsaid.
TOOLS = frozenset({
    "GitHub Copilot", "Codex", "ChatGPT", "OpenAI", "Cursor", "Aider", "Amazon Q", "Devin", "Jules", "Windsurf",
})


@dataclass(frozen=True)
class Model:
    vendor: str
    family: str
    version: str = ""

    @property
    def label(self) -> str:
        return f"{self.family} {self.version}".strip()

    @property
    def tool(self) -> bool:
        """True when this is a tool whose model is not named, and not a model."""
        return self.family in TOOLS


@dataclass(frozen=True)
class CoAuthor:
    name: str
    email: str
    model: Model | None = None
    kind: str = "co-authored-by"


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
    (re.compile(rf"\bqwen(?:[ -]?v?{_VERSION})?\b", re.I), "Alibaba", "Qwen"),
    (re.compile(rf"\bgrok\b(?:[ -]v?{_VERSION})?", re.I), "xAI", "Grok"),
    (re.compile(rf"\bllama\b(?:[ -]v?{_VERSION})?", re.I), "Meta", "Llama"),
]

# When the name says nothing, the e-mail address of the trailer may.
_EMAIL_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"@anthropic\.com$", re.I), "Anthropic", "Claude"),
    # The GitHub account of Claude's agent (anthropic-code-agent[bot]), found by its
    # number: a person whose login is Claude has another one.
    (re.compile(r"^242468646\+claude@users\.noreply\.github\.com$", re.I), "Anthropic", "Claude"),
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


_DATE_RE = re.compile(r"-\d{8}\b")
_OLD_CLAUDE_RE = re.compile(r"\bclaude-(\d+)(?:-(\d+))?-(opus|sonnet|haiku)\b", re.I)
_BARE_CLAUDE_RE = re.compile(r"claude(?:[ -]code)?", re.I)


def _spelled_out(identifier: str) -> str:
    """A model identifier as a name: "claude-opus-4-5-20251101" reads "claude-opus-4.5"."""
    text = _DATE_RE.sub("", identifier)
    text = _OLD_CLAUDE_RE.sub(lambda m: f"claude-{m[3]}-{m[1]}" + (f".{m[2]}" if m[2] else ""), text)
    return re.sub(r"(?<=\d)-(?=\d)", ".", text)


def assistant(name: str, email: str = "", rules: list[Rule] | None = None) -> Model | None:
    """The model an Assisted-by or Generated-by trailer names, or None.

    These trailers are often written "AGENT:MODEL-IDENTIFIER tool tool", without an
    address. The model identifier wins over the agent. A name that is not recognised
    stays unread: the line may name a person or a tool that is not an AI.
    """
    agent, _, identifier = name.partition(":")
    for text in (_spelled_out(identifier), _spelled_out(name), agent):
        found = identify(text.strip(), email, rules) if text.strip() else None
        if found:
            return found
    # "Claude" alone is a first name in a Co-Authored-By trailer. Here, written alone
    # and without an address, it is the assistant.
    if not email and _BARE_CLAUDE_RE.fullmatch(agent.strip()):
        return Model("Anthropic", "Claude")
    return None


def co_authors(message: str, rules: list[Rule] | None = None) -> list[CoAuthor]:
    """Every Co-Authored-By line of a commit message, models identified.

    Assisted-by and Generated-by lines are added when they name a model.
    """
    seen: set[tuple[str, str]] = set()
    result = []
    for found in TRAILER_RE.finditer(message):
        name = found.group("name").strip()
        email = (found.group("email") or "").strip()
        key = (name.lower(), email.lower())
        if key in seen or not (name or email):
            continue
        seen.add(key)
        kind = found.group("kind").lower()
        if kind == "co-authored-by":
            result.append(CoAuthor(name, email, identify(name, email, rules)))
            continue
        model = assistant(name, email, rules)
        if model:
            result.append(CoAuthor(name, email, model, kind))
    return result

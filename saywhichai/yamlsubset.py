"""A reader for the part of YAML a small configuration file is written in.

The standard library reads JSON and TOML, not YAML, and this project adds no
dependency for one file. This reader understands mappings, lists, strings, numbers,
true, false and null, comments, the short forms in brackets and braces, and the
blocks of text introduced by "|" or ">". A value stays on one line.

It does not understand anchors, aliases, tags, merge keys or several documents in
one file. It never guesses: what it does not understand raises YamlError, and the
caller treats the whole file as unreadable.
"""

from __future__ import annotations

import re

MAX_DEPTH = 20
_INT_RE = re.compile(r"^[-+]?[0-9]+$")
_FLOAT_RE = re.compile(r"^[-+]?([0-9]+\.[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?$")
_BLOCK_RE = re.compile(r"^([|>])(-?)$")
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "0": "\0", " ": " "}
_NO_PLAIN_START = "&*!|>@`%"


class YamlError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    """The line without its comment. A "#" inside quotes is not a comment."""
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if quote == '"' and char == "\\":
            index += 2
            continue
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"" and (index == 0 or line[index - 1] in " [{,:-"):
            quote = char
        elif char == "#" and (index == 0 or line[index - 1] == " "):
            return line[:index]
        index += 1
    return line


class _Inline:
    """A value written on one line: a scalar, or a short form in brackets or braces."""

    def __init__(self, text: str):
        self.text = text
        self.at = 0

    def fail(self, what: str) -> YamlError:
        return YamlError(f"{what} in {self.text!r}")

    def spaces(self) -> None:
        while self.at < len(self.text) and self.text[self.at] == " ":
            self.at += 1

    def value(self, stops: str, depth: int = 0):
        if depth > MAX_DEPTH:
            raise self.fail("too many levels")
        self.spaces()
        if self.at >= len(self.text):
            return None
        char = self.text[self.at]
        if char == "[":
            return self.sequence(depth)
        if char == "{":
            return self.mapping(depth)
        if char in "'\"":
            return self.quoted()
        start = self.at
        while self.at < len(self.text) and self.text[self.at] not in stops:
            self.at += 1
        return plain(self.text[start : self.at])

    def quoted(self) -> str:
        quote = self.text[self.at]
        self.at += 1
        parts = []
        while True:
            if self.at >= len(self.text):
                raise self.fail("a string is not closed")
            char = self.text[self.at]
            self.at += 1
            if quote == "'" and char == "'":
                if self.text[self.at : self.at + 1] == "'":
                    parts.append("'")
                    self.at += 1
                    continue
                return "".join(parts)
            if quote == '"' and char == '"':
                return "".join(parts)
            if quote == '"' and char == "\\":
                escape = self.text[self.at : self.at + 1]
                if escape not in _ESCAPES:
                    raise self.fail("an escape is not understood")
                parts.append(_ESCAPES[escape])
                self.at += 1
                continue
            parts.append(char)

    def sequence(self, depth: int) -> list:
        self.at += 1
        items = []
        while True:
            self.spaces()
            if self.at >= len(self.text):
                raise self.fail("a bracket is not closed")
            if self.text[self.at] == "]":
                self.at += 1
                return items
            if self.text[self.at] == ",":
                raise self.fail("an item is missing")
            items.append(self.value(",]", depth + 1))
            self.spaces()
            if self.text[self.at : self.at + 1] == ",":
                self.at += 1
            elif self.text[self.at : self.at + 1] != "]":
                raise self.fail("a comma is missing")

    def mapping(self, depth: int) -> dict:
        self.at += 1
        items: dict = {}
        while True:
            self.spaces()
            if self.at >= len(self.text):
                raise self.fail("a brace is not closed")
            if self.text[self.at] == "}":
                self.at += 1
                return items
            key = self.quoted() if self.text[self.at] in "'\"" else self.key()
            self.spaces()
            if self.text[self.at : self.at + 1] != ":":
                raise self.fail("a colon is missing")
            self.at += 1
            if key in items:
                raise self.fail(f"the key {key!r} is given twice")
            items[key] = self.value(",}", depth + 1)
            self.spaces()
            if self.text[self.at : self.at + 1] == ",":
                self.at += 1
            elif self.text[self.at : self.at + 1] != "}":
                raise self.fail("a comma is missing")

    def key(self) -> str:
        start = self.at
        while self.at < len(self.text) and self.text[self.at] not in ":,{}[]":
            self.at += 1
        key = self.text[start : self.at].strip()
        if not key:
            raise self.fail("a key is missing")
        return _key(key)

    def end(self) -> None:
        self.spaces()
        if self.at != len(self.text):
            raise self.fail("something follows the value")


def plain(text: str):
    """A value written without quotes."""
    text = text.strip()
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if text[0] in _NO_PLAIN_START or text[0] in "[]{}," or text == "<<":
        raise YamlError(f"not understood: {text!r}")
    if text in "-?:" or text[:2] in ("- ", "? ", ": ") or ": " in text or text.endswith(":"):
        raise YamlError(f"not understood: {text!r}")
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _key(text: str) -> str:
    if text[0] in _NO_PLAIN_START or text[0] in "?[]{}," or text == "<<" or text == "-" or text.startswith("- "):
        raise YamlError(f"a key is not understood: {text!r}")
    return text


def _inline(text: str):
    reader = _Inline(text)
    if text[:1] in "[{'\"":
        value = reader.value("")
        reader.end()
        return value
    return plain(text)


def _open(text: str) -> bool:
    """True when brackets or braces of the text are not closed yet."""
    depth = 0
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        if quote == '"' and char == "\\":
            index += 2
            continue
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        index += 1
    return depth > 0


def _split_key(text: str) -> tuple[str, str] | None:
    """The key and what follows it, when the line is "key: value" or "key:"."""
    if text[:1] in "'\"":
        reader = _Inline(text)
        key = reader.quoted()
        rest = text[reader.at :]
        if rest == ":" or rest.startswith(": "):
            return key, rest[1:].strip()
        return None
    if text[:1] in "[{":
        return None
    index = text.find(":")
    while index != -1:
        if index + 1 == len(text) or text[index + 1] == " ":
            key = text[:index].strip()
            return (_key(key), text[index + 1 :].strip()) if key else None
        index = text.find(":", index + 1)
    return None


class _Reader:
    def __init__(self, text: str):
        if re.search(r"^ *\t", text, re.MULTILINE):
            raise YamlError("a line is indented with a tab")
        self.raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.at = 0

    # A line of structure: (indent, text without comment), skipping blank lines.
    def peek(self) -> tuple[int, str] | None:
        while self.at < len(self.raw):
            line = _strip_comment(self.raw[self.at]).rstrip()
            if line.strip():
                return len(line) - len(line.lstrip(" ")), line.strip()
            self.at += 1
        return None

    def document(self):
        first = self.peek()
        if first and first[1] == "---":
            self.at += 1
            first = self.peek()
        if first is None:
            return None
        if first[1].startswith(("%", "---", "...")):
            raise YamlError("directives and several documents are not understood")
        value = self.block(first[0], 0)
        rest = self.peek()
        if rest is not None:
            raise YamlError(f"line {self.at + 1}: unexpected indentation or content")
        return value

    def block(self, indent: int, depth: int):
        if depth > MAX_DEPTH:
            raise YamlError("too many levels")
        line = self.peek()
        assert line is not None
        if line[1] == "-" or line[1].startswith("- "):
            return self.sequence(indent, depth)
        if _split_key(line[1]) is None:
            raise YamlError(f"line {self.at + 1}: neither a key nor a list item")
        return self.mapping(indent, depth)

    def mapping(self, indent: int, depth: int) -> dict:
        items: dict = {}
        while True:
            line = self.peek()
            if line is None or line[0] < indent:
                return items
            if line[0] > indent:
                raise YamlError(f"line {self.at + 1}: unexpected indentation")
            if line[1].startswith(("---", "...")):
                raise YamlError("several documents are not understood")
            pair = _split_key(line[1])
            if pair is None:
                raise YamlError(f"line {self.at + 1}: a key is expected")
            key, rest = pair
            if key in items:
                raise YamlError(f"line {self.at + 1}: the key {key!r} is given twice")
            self.at += 1
            items[key] = self.value(rest, indent, depth, in_mapping=True)

    def sequence(self, indent: int, depth: int) -> list:
        items = []
        while True:
            line = self.peek()
            if line is None or line[0] < indent:
                return items
            if line[0] > indent or not (line[1] == "-" or line[1].startswith("- ")):
                if line[0] == indent:
                    return items  # the list ends where the next key of the parent begins
                raise YamlError(f"line {self.at + 1}: unexpected indentation")
            rest = line[1][1:]
            inner = indent + 1 + (len(rest) - len(rest.lstrip(" ")))
            rest = rest.strip()
            if rest and (rest == "-" or rest.startswith("- ") or _split_key(rest) is not None):
                # A mapping or a list that begins on the line of the dash.
                self.raw[self.at] = " " * inner + rest
                items.append(self.block(inner, depth + 1))
                continue
            self.at += 1
            items.append(self.value(rest, indent, depth, in_mapping=False))

    def value(self, rest: str, indent: int, depth: int, in_mapping: bool):
        """What follows "key:" or "-": on the same line, or in the lines below."""
        header = _BLOCK_RE.match(rest)
        if header:
            return self.text_block(indent, header.group(1), header.group(2))
        if not rest:
            line = self.peek()
            if line is None or line[0] < indent:
                return None
            if line[0] > indent:
                return self.block(line[0], depth + 1)
            # A list may sit at the indentation of its key.
            if in_mapping and (line[1] == "-" or line[1].startswith("- ")):
                return self.sequence(indent, depth + 1)
            return None
        if rest[0] in "[{":
            while _open(rest):
                line = self.peek()
                if line is None or line[0] <= indent:
                    raise YamlError("a bracket or a brace is not closed")
                rest += " " + line[1]
                self.at += 1
            return _inline(rest)
        if rest[0] in "'\"":
            return _inline(rest)
        # A plain value stays on its line: one that goes on over the next lines is refused.
        value = plain(rest)
        line = self.peek()
        if line is not None and line[0] > indent:
            raise YamlError(f"line {self.at + 1}: unexpected indentation")
        return value

    def text_block(self, indent: int, style: str, chomp: str) -> str:
        """The lines under "|" (kept as they are) or ">" (joined into paragraphs)."""
        lines: list[str] = []
        inner = None
        while self.at < len(self.raw):
            raw = self.raw[self.at].rstrip()
            if raw.strip():
                width = len(raw) - len(raw.lstrip(" "))
                if width <= indent:
                    break
                inner = width if inner is None else inner
                if width < inner:
                    raise YamlError(f"line {self.at + 1}: unexpected indentation in a block of text")
                lines.append(raw[inner:])
            else:
                if inner is not None and len(self.raw[self.at]) > inner:
                    raise YamlError(f"line {self.at + 1}: spaces alone on a line of a block of text")
                lines.append("")
            self.at += 1
        while lines and not lines[-1]:
            lines.pop()
        if style == "|":
            text = "\n".join(lines)
        else:
            # Lines of one paragraph are joined; a blank line keeps its break.
            text = ""
            blank = 0
            previous = None
            for line in lines:
                if not line:
                    blank += 1
                    continue
                if line.startswith(" ") or (previous is None and blank):
                    raise YamlError("a block of text is laid out in a way that is not understood")
                if previous is None:
                    text = line
                elif blank:
                    text += "\n" * blank + line
                else:
                    text += " " + line
                blank = 0
                previous = line
        # The text ends with a line break unless "-" asks for none, or the file ends without one.
        cut = self.at >= len(self.raw) and bool(self.raw[-1].strip())
        if chomp == "-" or not text or cut:
            return text
        return text + "\n"


def load(text: str):
    """The value of the document, or YamlError when it holds something not understood."""
    return _Reader(text).document()

import pytest

from ai_disclosure.yamlsubset import YamlError, load


def test_mappings_lists_and_scalars():
    text = """\
# A comment
version: 1
name: plain text  # a comment after a value
quoted: "a # that is not a comment, and a \\"quote\\""
single: 'it''s'
yes: true
no: False
nothing: ~
empty:
ratio: 0.5
url: https://example.org/a#b
defaults:
  stance: generated
  disclosure: none
  deeper:
    list: [a, "b, c", 3]
    map: {key: value, other: [1, 2]}
items:
  - one
  - key: value
    more: 2
  -
    alone: true
  - [x, y]
same_indent:
- a
- b
after: end
"""
    assert load(text) == {
        "version": 1,
        "name": "plain text",
        "quoted": 'a # that is not a comment, and a "quote"',
        "single": "it's",
        "yes": True,
        "no": False,
        "nothing": None,
        "empty": None,
        "ratio": 0.5,
        "url": "https://example.org/a#b",
        "defaults": {
            "stance": "generated",
            "disclosure": "none",
            "deeper": {"list": ["a", "b, c", 3], "map": {"key": "value", "other": [1, 2]}},
        },
        "items": ["one", {"key": "value", "more": 2}, {"alone": True}, ["x", "y"]],
        "same_indent": ["a", "b"],
        "after": "end",
    }


def test_blocks_of_text():
    text = """\
folded: >-
  one
  two

  three # kept
literal: |
  one
   two
list: [a,
  b]
"""
    assert load(text) == {
        "folded": "one two\nthree # kept",
        "literal": "one\n two\n",
        "list": ["a", "b"],
    }


def test_a_document_marker_and_an_empty_file():
    assert load("---\na: 1\n") == {"a": 1}
    assert load("# nothing\n") is None


@pytest.mark.parametrize(
    "text",
    [
        "a: &anchor 1\nb: *anchor\n",
        "a: !!python/object:os.system x\n",
        "base: {a: 1}\nother:\n  <<: *base\n",
        "a: 1\n---\nb: 2\n",
        "%YAML 1.2\n---\na: 1\n",
        "a: 1\na: 2\n",
        "a:\n\tb: 1\n",
        "a: [1, 2\n",
        'a: "not closed\n',
        "a: 1\n  b: 2\n",
        "just a sentence\n",
        "a: |+\n  kept\n",
        "a: a value\n  that goes on\n",
        "a: x: y\n",
        "a: - x\n",
        "a: [,]\n",
        "a: [b, c: d]\n",
        "a:\n  b: 1\n  - c\n",
        "a: >-\n  x\n    deeper\n",
        "a: " + "[" * 50 + "]" * 50 + "\n",
    ],
)
def test_what_is_not_understood_is_refused(text):
    with pytest.raises(YamlError):
        load(text)

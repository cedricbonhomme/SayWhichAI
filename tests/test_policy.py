import pytest

from ai_disclosure.policy import PolicyError, link, read_policy

POLICY = """\
version: 1
summary: restrictive
statement: AI_POLICY.md
status: draft
exceptions: true
undecided: [models]
defaults:
  stance: generated
  disclosure: required
  humanReview: required
assertions:
  - scope: docs
    stance: generated
  - scope: code
    stance: assisted
autonomousAgents:
  allowed: false
disclosureFormat:
  method: [commit-trailer, pr-template]
  trailers:
    assisted: "Assisted-by:"
    generated: "Generated-by:"
  content: [tool, model]
unknown-field: kept for a later version
"""


def test_the_fields_the_site_shows():
    assert read_policy(POLICY) == {
        "readable": True,
        "summary": "restrictive",
        "status": "draft",
        "exceptions": True,
        "undecided": ["models"],
        "statement": "AI_POLICY.md",
        "stance": "assisted",  # what the file says for code wins over the defaults
        "disclosure": "required",
        "human_review": "required",
        "agents": False,
        "method": ["commit-trailer", "pr-template"],
        "trailers": ["Assisted-by", "Generated-by"],
        "content": ["tool", "model"],
        "scopes": ["docs"],
    }


def test_a_file_that_only_says_neutral():
    policy = read_policy("version: 1\nsummary: neutral\nstatement: CONTRIBUTING.md\n")
    assert policy["summary"] == "neutral"
    assert (policy["stance"], policy["disclosure"], policy["agents"]) == (None, None, None)


def test_none_is_a_value_not_nothing():
    assert read_policy("version: 1\ndefaults:\n  disclosure: none\n")["disclosure"] == "none"


def test_a_single_trailer():
    policy = read_policy('version: 1\ndisclosureFormat:\n  trailer: "Co-Authored-By:"\n')
    assert policy["trailers"] == ["Co-Authored-By"]


@pytest.mark.parametrize(
    "text",
    [
        "summary: mixed\n",  # no version
        "version: 2\n",
        "version: true\n",
        "version: 1\ndefaults:\n  stance: sometimes\n",
        "version: 1\ndefaults: generated\n",
        "version: 1\nautonomousAgents:\n  allowed: maybe\n",
        "version: 1\ndisclosureFormat:\n  method: commit-trailer\n",
        "version: 1\nstatement: [a, b]\n",
        "version: 1\nassertions:\n  - stance: generated\n",
        "version: 1\na: &x 1\n",
        "- a list\n",
        "",
    ],
)
def test_a_file_that_is_not_understood_is_refused(text):
    with pytest.raises(PolicyError):
        read_policy(text)


def test_a_pointer_becomes_an_address():
    base = "https://github.com/demo/demo/blob/HEAD"
    assert link(base, "AI_POLICY.md") == base + "/AI_POLICY.md"
    assert link(base, "docs/ai policy.md#the rules") == base + "/docs/ai%20policy.md#the%20rules"
    assert link(base, "https://example.org/policy") == "https://example.org/policy"
    assert link(base, "../../../other/repo") == base + "/other/repo"


@pytest.mark.parametrize("pointer", ["javascript:alert(1)", "data:text/html,x", "//example.org/x", "", "https://exa mple.org"])
def test_only_web_addresses_and_paths_are_kept(pointer):
    assert link("https://github.com/demo/demo/blob/HEAD", pointer) == ""

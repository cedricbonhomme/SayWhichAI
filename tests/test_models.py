import pytest

from ai_disclosure.models import Model, co_authors, identify


@pytest.mark.parametrize(
    "name, email, expected",
    [
        ("Claude Fable 5", "noreply@anthropic.com", Model("Anthropic", "Claude Fable", "5")),
        ("Claude Opus 4.8 (1M context)", "noreply@anthropic.com", Model("Anthropic", "Claude Opus", "4.8")),
        ("Claude", "noreply@anthropic.com", Model("Anthropic", "Claude")),
        ("GPT-6", "noreply@openai.com", Model("OpenAI", "GPT", "6")),
        ("Codex (GPT-6)", "noreply@openai.com", Model("OpenAI", "GPT", "6")),
        ("Codex", "noreply@openai.com", Model("OpenAI", "Codex")),
        ("Copilot Autofix powered by AI", "x@users.noreply.github.com", Model("GitHub", "GitHub Copilot")),
        ("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com", Model("GitHub", "GitHub Copilot")),
        ("anthropic-code-agent[bot]", "242468646+Claude@users.noreply.github.com", Model("Anthropic", "Claude")),
        ("Claude", "242468646+Claude@users.noreply.github.com", Model("Anthropic", "Claude")),
    ],
)
def test_models_are_recognised(name, email, expected):
    assert identify(name, email) == expected


@pytest.mark.parametrize(
    "name, email",
    [
        ("Xavier Claude", "contact@example.org"),
        ("Devin Smith", "devin@example.org"),
        ("Jules Verne", "jules@example.org"),
        ("cedricbonhomme", "465400+cedricbonhomme@users.noreply.github.com"),
        ("Claude", "1234+Claude@users.noreply.github.com"),
    ],
)
def test_people_are_not_models(name, email):
    assert identify(name, email) is None


def test_a_tool_is_not_a_model():
    # Copilot runs on the models of several vendors and does not say which one.
    assert identify("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com").tool
    assert identify("Codex", "noreply@openai.com").tool
    # A model named beside the tool is a model.
    assert not identify("Codex (GPT-6)", "noreply@openai.com").tool
    assert not identify("Claude Opus 5.5", "noreply@anthropic.com").tool


def test_trailers_are_read_whatever_their_case():
    message = (
        "fix: something\n\nA body.\n\n"
        "Co-authored-by: Ada Lovelace <ada@example.org>\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
    )
    found = co_authors(message)
    assert [author.name for author in found] == ["Ada Lovelace", "Claude Opus 5.5"]
    assert found[0].model is None
    assert found[1].model is not None
    assert found[1].model.label == "Claude Opus 5.5"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Assisted-by: Claude:claude-opus-4-5", Model("Anthropic", "Claude Opus", "4.5")),
        ("Assisted-by: Claude Code:claude-opus-5-5-20261001", Model("Anthropic", "Claude Opus", "5.5")),
        ("Assisted-by: Claude:claude-3-opus coccinelle sparse", Model("Anthropic", "Claude Opus", "3")),
        ("assisted-by: GitHub Copilot:claude-sonnet-4.5", Model("Anthropic", "Claude Sonnet", "4.5")),
        ("Assisted-by: OpenCode:qwen3-coder", Model("Alibaba", "Qwen", "3")),
        ("Assisted-by: Claude Code", Model("Anthropic", "Claude")),
        ("Generated-by: Claude Opus 5.5 <noreply@anthropic.com>", Model("Anthropic", "Claude Opus", "5.5")),
        ("Generated-by: Gemini:gemini-2.5-pro", Model("Google", "Gemini Pro", "2.5")),
    ],
)
def test_assisted_by_and_generated_by_name_a_model(line, expected):
    found = co_authors(f"fix: something\n\n{line}\n")
    assert [author.model for author in found] == [expected]
    assert found[0].kind == line.split(":")[0].lower()


@pytest.mark.parametrize(
    "line",
    [
        "Assisted-by: Claude Paroz <claude@example.org>",
        "Assisted-by: Claude <claude@example.org>",
        "Assisted-by: Ada Lovelace <ada@example.org>",
        "Assisted-by: Devin Smith",
        "Assisted-by: coccinelle",
        "Generated-by: a script of mine",
    ],
)
def test_assisted_by_a_person_or_another_tool_is_left_unread(line):
    # Neither a model nor a co-author: the line does not say that a person wrote the commit.
    assert co_authors(f"fix: something\n\n{line}\n") == []


def test_the_same_model_in_two_trailers_is_one_model():
    message = (
        "fix: something\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
        "Assisted-by: Claude Code:claude-opus-5-5\n"
    )
    assert {author.model for author in co_authors(message)} == {Model("Anthropic", "Claude Opus", "5.5")}


def test_qwen_is_read_with_its_version_attached():
    assert identify("Qwen3-Coder") == Model("Alibaba", "Qwen", "3")
    assert identify("Qwentin Martin", "q@example.org") is None

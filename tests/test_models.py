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
    ],
)
def test_people_are_not_models(name, email):
    assert identify(name, email) is None


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
    assert found[1].model.label == "Claude Opus 5.5"

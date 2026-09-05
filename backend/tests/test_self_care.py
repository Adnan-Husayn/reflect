import ast
import dataclasses
import inspect

import pytest

from app.content import self_care
from app.content.self_care import CONFLICT, INSUFFICIENT, LOW_VALENCE, PROMPTS, STEADY, prompts_for

# Anything that would read as naming a condition rather than an observation.
DIAGNOSTIC_WORDS = (
    "diagnos",
    "depress",
    "disorder",
    "anxiety disorder",
    "illness",
    "symptom",
    "severe",
    "moderate",
    "mild",
    "at risk",
    "you are",
)


FORBIDDEN_IMPORTS = {
    "openai",
    "anthropic",
    "httpx",
    "requests",
    "urllib",
    "socket",
    "transformers",
    "torch",
}


def test_the_library_reaches_nothing_that_could_generate_text():
    """The one place in this project where a language model must not appear.

    Checks the imports rather than the prose: the module's own docstring says
    the word "generated", and a substring search would flag its documentation.
    """
    tree = ast.parse(inspect.getsource(self_care))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert imported & FORBIDDEN_IMPORTS == set(), imported & FORBIDDEN_IMPORTS


def test_the_prompts_are_module_level_constants():
    """Not built at call time, so what ships is what was reviewed."""
    assert isinstance(PROMPTS, dict)
    assert all(type(prompt).__name__ == "Prompt" for prompt in PROMPTS.values())
    # frozen dataclass: nothing can rewrite a prompt at runtime.
    with pytest.raises(dataclasses.FrozenInstanceError):
        next(iter(PROMPTS.values())).observation = "rewritten"


def test_every_observation_key_maps_to_a_prompt():
    assert set(PROMPTS) == {LOW_VALENCE, CONFLICT, STEADY, INSUFFICIENT}


def test_every_prompt_declares_the_key_it_is_stored_under():
    for key, prompt in PROMPTS.items():
        assert prompt.key == key


def test_no_prompt_names_a_condition():
    for prompt in PROMPTS.values():
        text = f"{prompt.observation} {prompt.suggestion}".lower()
        for word in DIAGNOSTIC_WORDS:
            assert word not in text, f"{prompt.key} contains {word!r}"


def test_prompts_describe_observations_rather_than_states():
    """Each one talks about readings, not about the person."""
    for key in (LOW_VALENCE, CONFLICT):
        text = PROMPTS[key].observation.lower()
        assert "reading" in text or "channel" in text


def test_the_steady_prompt_does_not_claim_a_good_week():
    text = PROMPTS[STEADY].suggestion.lower()
    assert "does not mean a good one" in text


def test_the_insufficient_prompt_says_nothing_is_being_withheld():
    assert "withheld" in PROMPTS[INSUFFICIENT].suggestion.lower()


# ── mapping ───────────────────────────────────────────────────────────


def test_insufficient_data_returns_only_its_own_prompt():
    prompts = prompts_for(status=INSUFFICIENT, sustained_low_valence=True, sustained_conflict=True)
    assert [prompt.key for prompt in prompts] == [INSUFFICIENT]


def test_a_steady_week_returns_only_the_steady_prompt():
    prompts = prompts_for(status=STEADY, sustained_low_valence=False, sustained_conflict=False)
    assert [prompt.key for prompt in prompts] == [STEADY]


def test_each_raised_observation_returns_its_prompt():
    both = prompts_for(status="observations", sustained_low_valence=True, sustained_conflict=True)
    assert [prompt.key for prompt in both] == [LOW_VALENCE, CONFLICT]

    one = prompts_for(status="observations", sustained_low_valence=False, sustained_conflict=True)
    assert [prompt.key for prompt in one] == [CONFLICT]


def test_no_observation_raised_returns_nothing_rather_than_inventing_advice():
    prompts = prompts_for(status="observations", sustained_low_valence=False, sustained_conflict=False)
    assert prompts == []

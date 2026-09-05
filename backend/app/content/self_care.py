"""Self-care prompts: a static, hand-written, rule-mapped library.

**Nothing here is generated at runtime, and no language model is involved.**
This is the single place in the project where that must hold: generated advice
delivered on a sustained-distress trigger is the one thing this app could do
that would actually hurt someone.

Each prompt is tied to an *observation* rather than a state, and none of them is
medical advice. Deliberately few, and plain in tone — a long list of cheerful
suggestions reads as a system that thinks it knows what is wrong.
"""

from collections.abc import Sequence
from dataclasses import dataclass

# Observation keys the assessment can raise. A prompt exists for each one, and
# a test asserts that mapping stays total in both directions.
LOW_VALENCE = "sustained_low_valence"
CONFLICT = "sustained_conflict"
STEADY = "steady"
INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class Prompt:
    key: str
    observation: str
    suggestion: str


PROMPTS: dict[str, Prompt] = {
    LOW_VALENCE: Prompt(
        key=LOW_VALENCE,
        observation="More of your readings than usual have been low-valence this week.",
        suggestion=(
            "If that matches how the week felt, it can help to tell one person you trust. "
            "If it does not match, the readings are worth doubting rather than you."
        ),
    ),
    CONFLICT: Prompt(
        key=CONFLICT,
        observation=(
            "Your channels disagreed with each other on several days this week — "
            "what you said and how you sounded or looked did not line up."
        ),
        suggestion=(
            "This often just means the models are uncertain, or the lighting and microphone "
            "were poor. It is only worth a thought if it matches something you noticed yourself."
        ),
    ),
    STEADY: Prompt(
        key=STEADY,
        observation="Nothing in this week's readings stood out from your usual range.",
        suggestion=(
            "That is a statement about the readings, not about you. "
            "A steady week here does not mean a good one."
        ),
    ),
    INSUFFICIENT: Prompt(
        key=INSUFFICIENT,
        observation="There are not enough recorded days yet to say anything about this week.",
        suggestion=(
            "Record a few more sessions and this will start to fill in. "
            "Nothing is being withheld from you — there is genuinely nothing measured yet."
        ),
    ),
}


def prompts_for(*, status: str, sustained_low_valence: bool, sustained_conflict: bool) -> list[Prompt]:
    """Map an assessment onto its prompts. Pure lookup — nothing is composed."""
    if status == INSUFFICIENT:
        return [PROMPTS[INSUFFICIENT]]
    if status == STEADY:
        return [PROMPTS[STEADY]]

    keys: Sequence[str] = [
        key
        for key, raised in ((LOW_VALENCE, sustained_low_valence), (CONFLICT, sustained_conflict))
        if raised
    ]
    return [PROMPTS[key] for key in keys]

"""PHQ-8.

PHQ-8 rather than PHQ-9: it drops PHQ-9's ninth item, which asks about thoughts
of self-harm. That is standard practice for research use precisely because
collecting it creates a duty of response this project is not equipped to meet.

The definition lives on the server so the form renders from it and the two
cannot drift, and so the score can be recomputed from the item responses
instead of trusted from the client.

**No severity bands.** The instrument is scored and the number is shown; it is
never mapped to "mild", "moderately severe" or a cutpoint verdict. The research
question needs the value, not an interpretation, and a band would add
clinical-interpretation risk for no analytical gain.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str
    text: str


@dataclass(frozen=True)
class Option:
    value: int
    label: str


@dataclass(frozen=True)
class Instrument:
    code: str
    name: str
    prompt: str
    items: tuple[Item, ...]
    options: tuple[Option, ...]

    @property
    def max_score(self) -> int:
        return len(self.items) * max(option.value for option in self.options)

    @property
    def item_ids(self) -> set[str]:
        return {item.id for item in self.items}

    @property
    def allowed_values(self) -> set[int]:
        return {option.value for option in self.options}


PHQ8 = Instrument(
    code="PHQ-8",
    name="Patient Health Questionnaire-8",
    prompt="Over the last 2 weeks, how often have you been bothered by any of the following problems?",
    items=(
        Item("q1", "Little interest or pleasure in doing things"),
        Item("q2", "Feeling down, depressed, or hopeless"),
        Item("q3", "Trouble falling or staying asleep, or sleeping too much"),
        Item("q4", "Feeling tired or having little energy"),
        Item("q5", "Poor appetite or overeating"),
        Item(
            "q6",
            "Feeling bad about yourself — or that you are a failure, "
            "or have let yourself or your family down",
        ),
        Item("q7", "Trouble concentrating on things, such as reading or watching television"),
        Item(
            "q8",
            "Moving or speaking so slowly that other people could have noticed — or the opposite, "
            "being so fidgety or restless that you have been moving around a lot more than usual",
        ),
    ),
    options=(
        Option(0, "Not at all"),
        Option(1, "Several days"),
        Option(2, "More than half the days"),
        Option(3, "Nearly every day"),
    ),
)


def score_responses(instrument: Instrument, responses: Mapping[str, int]) -> int:
    """Recompute the total from the item responses.

    Raises ValueError rather than scoring a partial or malformed submission: a
    total computed over missing items is not comparable with a complete one, and
    silently treating an absent answer as zero would bias every score downward.
    """
    provided = set(responses)
    missing = instrument.item_ids - provided
    if missing:
        raise ValueError(f"Missing responses for: {', '.join(sorted(missing))}.")

    unknown = provided - instrument.item_ids
    if unknown:
        raise ValueError(f"Unknown items: {', '.join(sorted(unknown))}.")

    allowed = instrument.allowed_values
    out_of_range = {item: value for item, value in responses.items() if int(value) not in allowed}
    if out_of_range:
        options = ", ".join(str(value) for value in sorted(allowed))
        raise ValueError(f"Responses must be one of {options}; got {out_of_range}.")

    return sum(int(value) for value in responses.values())

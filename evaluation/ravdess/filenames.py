"""Parse RAVDESS filenames into labelled records.

Every RAVDESS file encodes its own metadata in seven hyphen-separated numeric
fields, so there is no separate annotation file to join against::

    01-01-05-02-01-02-14.mp4
    |  |  |  |  |  |  +-- actor          01..24  (odd male, even female)
    |  |  |  |  |  +----- repetition     01, 02
    |  |  |  |  +-------- statement      01, 02
    |  |  |  +----------- intensity      01 normal, 02 strong
    |  |  +-------------- emotion        01..08
    |  +----------------- vocal channel  01 speech, 02 song
    +-------------------- modality       01 full AV, 02 video only, 03 audio only

Two properties of the corpus matter more than the rest of the encoding:

1. Both statements are semantically neutral. Whatever emotion an actor performs,
   the *words* carry none of it, so the transcript-text channel has a known
   ground truth of "neutral" on every single clip.
2. That makes every non-neutral clip a labelled cross-channel conflict, and
   every neutral clip a labelled agreement -- which is what lets the conflict
   threshold be derived rather than guessed.
"""

from dataclasses import dataclass
from pathlib import Path

# The seven canonical labels the API normalizes every model onto. Duplicated
# from app.schemas.emotion rather than imported: the harness runs against a
# deployed API over HTTP and must not depend on the backend package.
CANONICAL_EMOTIONS = (
    "anger",
    "disgust",
    "fear",
    "joy",
    "neutral",
    "sadness",
    "surprise",
)

MODALITIES = {"01": "full_av", "02": "video_only", "03": "audio_only"}
VOCAL_CHANNELS = {"01": "speech", "02": "song"}
INTENSITIES = {"01": "normal", "02": "strong"}

# RAVDESS emotion codes mapped onto the canonical vocabulary.
#
# "calm" (02) has no canonical equivalent. It is merged into neutral by default,
# which is the common treatment in the literature, but the choice is a real one
# and `calm_policy` keeps it visible instead of burying it in a dict.
EMOTION_CODES = {
    "01": "neutral",
    "02": "calm",
    "03": "joy",
    "04": "sadness",
    "05": "anger",
    "06": "fear",
    "07": "disgust",
    "08": "surprise",
}

STATEMENTS = {
    "01": "Kids are talking by the door",
    "02": "Dogs are sitting by the door",
}

# Both statements are emotionally inert, so this is the text channel's label on
# every clip in the corpus.
STATEMENT_GROUND_TRUTH = "neutral"

FIELD_COUNT = 7


class RavdessFilenameError(ValueError):
    """Raised when a filename does not follow the seven-field RAVDESS encoding."""


@dataclass(frozen=True, slots=True)
class Clip:
    """One RAVDESS recording and everything its filename tells us about it."""

    path: Path
    modality: str
    vocal_channel: str
    emotion: str
    intensity: str
    statement: str
    statement_text: str
    repetition: int
    actor: int

    @property
    def actor_sex(self) -> str:
        """Odd-numbered actors are male, even-numbered female."""
        return "male" if self.actor % 2 else "female"

    @property
    def text_label(self) -> str:
        """Ground truth for the transcript-text channel.

        Always neutral: the spoken sentence carries no emotional content, which
        is precisely what makes the corpus useful for conflict work.
        """
        return STATEMENT_GROUND_TRUTH

    @property
    def is_conflict(self) -> bool:
        """Whether text and voice/face ground truths disagree on this clip.

        True for every performed emotion other than neutral. This is the binary
        label the conflict threshold's ROC curve is drawn against.
        """
        return self.emotion != STATEMENT_GROUND_TRUTH


def parse_filename(path: str | Path, calm_policy: str = "neutral") -> Clip | None:
    """Read one RAVDESS filename into a Clip.

    `calm_policy` decides what happens to the "calm" class, which has no
    canonical equivalent:

    - "neutral" merges it into neutral (default, and the usual choice)
    - "drop"    returns None so the caller skips the clip

    Returns None only for dropped calm clips. Anything genuinely malformed
    raises, because a filename this harness cannot read is a data problem worth
    stopping on rather than silently skipping.
    """
    if calm_policy not in {"neutral", "drop"}:
        raise ValueError("calm_policy must be 'neutral' or 'drop'.")

    path = Path(path)
    fields = path.stem.split("-")
    if len(fields) != FIELD_COUNT:
        raise RavdessFilenameError(f"{path.name}: expected {FIELD_COUNT} fields, found {len(fields)}.")

    modality, vocal_channel, emotion_code, intensity, statement, repetition, actor = fields

    for value, table, name in (
        (modality, MODALITIES, "modality"),
        (vocal_channel, VOCAL_CHANNELS, "vocal channel"),
        (emotion_code, EMOTION_CODES, "emotion"),
        (intensity, INTENSITIES, "intensity"),
        (statement, STATEMENTS, "statement"),
    ):
        if value not in table:
            raise RavdessFilenameError(f"{path.name}: unknown {name} code {value!r}.")

    emotion = EMOTION_CODES[emotion_code]
    if emotion == "calm":
        if calm_policy == "drop":
            return None
        emotion = "neutral"

    try:
        actor_number = int(actor)
        repetition_number = int(repetition)
    except ValueError as error:
        raise RavdessFilenameError(f"{path.name}: actor and repetition must be numeric.") from error

    if not 1 <= actor_number <= 24:
        raise RavdessFilenameError(f"{path.name}: actor {actor_number} outside the range 1-24.")

    return Clip(
        path=path,
        modality=MODALITIES[modality],
        vocal_channel=VOCAL_CHANNELS[vocal_channel],
        emotion=emotion,
        intensity=INTENSITIES[intensity],
        statement=statement,
        statement_text=STATEMENTS[statement],
        repetition=repetition_number,
        actor=actor_number,
    )

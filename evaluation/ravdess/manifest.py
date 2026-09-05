"""Build the clip manifest and split it so no actor appears on both sides.

The split is the part of this harness most worth getting right. RAVDESS has 24
actors each performing the same two sentences in all eight emotions, so a naive
random split over clips puts the same face and the same voice in both training
and held-out data. A model then partly learns "this is actor 14" instead of
"this is anger", and every number the harness reports comes out inflated.

Splitting by actor removes that. The held-out actors are people the model has
never seen, which is the only setting in which the reported accuracy means what
a reader will assume it means.
"""

import csv
import json
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .filenames import Clip, parse_filename

# Actors 19-24 held out by default. The tail happens to be sex-balanced -- three
# odd-numbered (male) and three even-numbered (female) -- so the default split
# needs no special pleading. Override it if you want a different partition, but
# keep it actor-disjoint.
DEFAULT_HELD_OUT_ACTORS = (19, 20, 21, 22, 23, 24)

MEDIA_SUFFIXES = (".mp4", ".wav")


@dataclass(frozen=True, slots=True)
class ManifestRow:
    """One clip, with the split it belongs to and the label for each channel."""

    path: str
    actor: int
    actor_sex: str
    split: str
    modality: str
    vocal_channel: str
    intensity: str
    statement: str
    statement_text: str
    repetition: int
    # Ground truth per channel. voice and face share the performed emotion;
    # text is neutral on every clip because the sentences carry no emotion.
    voice_label: str
    face_label: str
    text_label: str
    # Whether text disagrees with voice/face, i.e. the binary target the
    # conflict threshold's ROC curve is drawn against.
    is_conflict: bool


def discover_clips(
    root: Path,
    calm_policy: str = "neutral",
    vocal_channel: str = "speech",
    modality: str = "full_av",
) -> Iterator[Clip]:
    """Walk an extracted RAVDESS tree and yield the clips we intend to score.

    Defaults to full audio-video speech, which is the only combination that
    carries all three channels on the same labelled instance. Song is excluded
    by default: it covers only six of the eight emotions and actor 18 has none
    of it, so including it would quietly unbalance the classes.
    """
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        clip = parse_filename(path, calm_policy=calm_policy)
        if clip is None:
            continue
        if clip.vocal_channel != vocal_channel or clip.modality != modality:
            continue
        yield clip


def build_manifest(
    clips: Iterable[Clip],
    held_out_actors: Sequence[int] = DEFAULT_HELD_OUT_ACTORS,
) -> list[ManifestRow]:
    """Label every clip with its split, keeping the partition actor-disjoint."""
    held_out = set(held_out_actors)
    if not held_out:
        raise ValueError("At least one actor must be held out.")
    if not held_out.issubset(range(1, 25)):
        raise ValueError("Held-out actors must be numbered 1-24.")
    if len(held_out) == 24:
        raise ValueError("Holding out every actor leaves nothing to fit on.")

    return [
        ManifestRow(
            path=str(clip.path),
            actor=clip.actor,
            actor_sex=clip.actor_sex,
            split="held_out" if clip.actor in held_out else "train",
            modality=clip.modality,
            vocal_channel=clip.vocal_channel,
            intensity=clip.intensity,
            statement=clip.statement,
            statement_text=clip.statement_text,
            repetition=clip.repetition,
            voice_label=clip.emotion,
            face_label=clip.emotion,
            text_label=clip.text_label,
            is_conflict=clip.is_conflict,
        )
        for clip in clips
    ]


def assert_actor_disjoint(rows: Sequence[ManifestRow]) -> None:
    """Fail loudly if any actor appears in both splits.

    Called by the build script rather than left to inspection: a leak here is
    invisible in the output and inflates every downstream number.
    """
    actors_by_split: dict[str, set[int]] = {}
    for row in rows:
        actors_by_split.setdefault(row.split, set()).add(row.actor)

    train = actors_by_split.get("train", set())
    held_out = actors_by_split.get("held_out", set())
    overlap = train & held_out
    if overlap:
        raise AssertionError(f"Actors appear in both splits: {sorted(overlap)}.")
    if not train or not held_out:
        raise AssertionError("Both splits must be non-empty.")


def summarize(rows: Sequence[ManifestRow]) -> dict[str, object]:
    """Counts worth reading before spending five weeks on the data."""
    per_split = Counter(row.split for row in rows)
    return {
        "clips": len(rows),
        "per_split": dict(per_split),
        "actors_per_split": {
            split: sorted({row.actor for row in rows if row.split == split}) for split in sorted(per_split)
        },
        "emotion_counts": {
            split: dict(Counter(row.voice_label for row in rows if row.split == split))
            for split in sorted(per_split)
        },
        "conflict_balance": {
            split: dict(
                Counter("conflict" if row.is_conflict else "aligned" for row in rows if row.split == split)
            )
            for split in sorted(per_split)
        },
    }


def write_manifest(rows: Sequence[ManifestRow], destination: Path) -> None:
    """Write the manifest as CSV. Every later stage reads this one file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def read_manifest(source: Path) -> list[ManifestRow]:
    """Read a manifest back, restoring the non-string field types."""
    with source.open(newline="", encoding="utf-8") as handle:
        return [
            ManifestRow(
                **{
                    **record,
                    "actor": int(record["actor"]),
                    "repetition": int(record["repetition"]),
                    "is_conflict": record["is_conflict"] == "True",
                }
            )
            for record in csv.DictReader(handle)
        ]


def write_summary(summary: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

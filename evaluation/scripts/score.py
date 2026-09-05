"""Step 3 — score every prepared clip through the running API.

    uvicorn app.main:app            # in backend/, first
    python scripts/score.py --manifest data/manifest.csv --prepared data/prepared \
        --split held_out --out data/scores.jsonl

Deliberately talks to the deployed API over HTTP rather than importing the model
wrappers. What we want to measure is the thing the live session actually calls,
including the normalization and smoothing that sit in front of the checkpoints.

Writes JSONL, one record per clip, appending as it goes so a long run can be
interrupted and resumed without losing what it already scored.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravdess.filenames import CANONICAL_EMOTIONS
from ravdess.manifest import ManifestRow, read_manifest

REQUEST_TIMEOUT = 120.0


def average_scores(vectors: list[dict[str, float]]) -> dict[str, float] | None:
    """Mean of several score vectors, mirroring the live session's smoothing.

    The running app smooths the facial channel over five frames before showing
    it, so evaluating a single frame would measure something the user never
    sees.
    """
    if not vectors:
        return None
    return {
        emotion: sum(vector.get(emotion, 0.0) for vector in vectors) / len(vectors)
        for emotion in CANONICAL_EMOTIONS
    }


def score_text(client: httpx.Client, text: str) -> dict[str, Any] | None:
    response = client.post("/predict/text", json={"text": text})
    if response.status_code != 200:
        return None
    return response.json()


def score_audio(client: httpx.Client, audio_path: Path) -> dict[str, Any] | None:
    """Score the voice channel without transcribing. /predict/audio exists for this."""
    with audio_path.open("rb") as handle:
        response = client.post("/predict/audio", files={"file": (audio_path.name, handle, "audio/wav")})
    if response.status_code != 200:
        return None
    return response.json()


def score_live_audio(client: httpx.Client, audio_path: Path) -> dict[str, Any] | None:
    """Transcribe and score in one call, so transcript quality can be measured too."""
    with audio_path.open("rb") as handle:
        response = client.post("/predict/live/audio", files={"file": (audio_path.name, handle, "audio/wav")})
    if response.status_code != 200:
        return None
    return response.json()


def score_frames(client: httpx.Client, frame_dir: Path) -> tuple[dict[str, float] | None, int, int]:
    """Score every sampled frame and average them. Returns (scores, scored, no_face)."""
    vectors: list[dict[str, float]] = []
    no_face = 0
    frames = sorted(frame_dir.glob("*.jpg"))
    for frame in frames:
        with frame.open("rb") as handle:
            response = client.post("/predict/facial", files={"file": (frame.name, handle, "image/jpeg")})
        if response.status_code == 400:
            # No detectable face. A real outcome for this corpus, not an error:
            # count it rather than dropping it silently.
            no_face += 1
            continue
        if response.status_code != 200:
            continue
        vectors.append(response.json()["scores"])
    return average_scores(vectors), len(vectors), no_face


def fuse(client: httpx.Client, channels: dict[str, dict[str, float]]) -> dict[str, Any] | None:
    if len(channels) < 2:
        return None
    response = client.post("/analyze/fusion", json=channels)
    if response.status_code != 200:
        return None
    return response.json()


def score_clip(
    client: httpx.Client,
    row: ManifestRow,
    prepared: Path,
    text_source: str,
) -> dict[str, Any]:
    stem = Path(row.path).stem
    audio_path = prepared / "audio" / f"{stem}.wav"
    frame_dir = prepared / "frames" / stem

    record: dict[str, Any] = {
        "clip": stem,
        "actor": row.actor,
        "split": row.split,
        "intensity": row.intensity,
        "truth": {"voice": row.voice_label, "face": row.face_label, "text": row.text_label},
        "is_conflict": row.is_conflict,
    }

    if text_source == "transcript":
        live = score_live_audio(client, audio_path) if audio_path.is_file() else None
        record["transcript"] = live.get("transcript") if live else None
        record["reference_text"] = row.statement_text
        voice = (live or {}).get("audio_prediction")
        text = (live or {}).get("text_prediction")
    else:
        voice = score_audio(client, audio_path) if audio_path.is_file() else None
        text = score_text(client, row.statement_text)

    face_scores, frames_scored, no_face = (
        score_frames(client, frame_dir) if frame_dir.is_dir() else (None, 0, 0)
    )

    record["voice"] = voice
    record["text"] = text
    record["face"] = {"scores": face_scores} if face_scores else None
    record["frames_scored"] = frames_scored
    record["frames_without_face"] = no_face

    channels = {
        name: value["scores"]
        for name, value in (("text", text), ("voice", voice), ("face", record["face"]))
        if value and value.get("scores")
    }
    record["fusion"] = fuse(client, channels)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--prepared", type=Path, default=Path("data/prepared"))
    parser.add_argument("--out", type=Path, default=Path("data/scores.jsonl"))
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--split", choices=("train", "held_out", "all"), default="held_out")
    parser.add_argument(
        "--text-source",
        choices=("statement", "transcript"),
        default="statement",
        help=(
            "'statement' scores the known sentence, isolating the emotion models from "
            "transcription error. 'transcript' scores what Whisper actually heard, which "
            "is what the live session does. Run both; report both."
        ),
    )
    parser.add_argument("--limit", type=int, default=0, help="Score only the first N clips (smoke test).")
    args = parser.parse_args()

    if not args.manifest.is_file():
        parser.error(f"{args.manifest} not found. Run build_manifest.py first.")

    rows = read_manifest(args.manifest)
    if args.split != "all":
        rows = [row for row in rows if row.split == args.split]
    if args.limit:
        rows = rows[: args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    already = set()
    if args.out.exists():
        with args.out.open(encoding="utf-8") as handle:
            already = {json.loads(line)["clip"] for line in handle if line.strip()}
        print(f"Resuming: {len(already)} clips already scored.")

    with (
        httpx.Client(base_url=args.api, timeout=REQUEST_TIMEOUT) as client,
        args.out.open("a", encoding="utf-8") as sink,
    ):
        health = client.get("/health")
        if health.status_code != 200:
            parser.error(f"API at {args.api} is not answering /health.")
        print(f"API health: {health.json()}")

        for index, row in enumerate(rows, start=1):
            stem = Path(row.path).stem
            if stem in already:
                continue
            record = score_clip(client, row, args.prepared, args.text_source)
            sink.write(json.dumps(record) + "\n")
            sink.flush()
            if index % 25 == 0:
                print(f"  {index}/{len(rows)} clips scored", flush=True)

    print(f"\nWrote scores to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

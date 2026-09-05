"""Step 2 — split every clip in the manifest into audio and frames.

    python scripts/extract_media.py --manifest data/manifest.csv --out data/prepared

Slow and IO-bound, but idempotent: clips whose outputs already exist are
skipped, so an interrupted run can simply be restarted.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravdess.manifest import read_manifest
from ravdess.media import (
    DEFAULT_FRAME_COUNT,
    MediaExtractionError,
    extract_clip,
    ffmpeg_available,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/prepared"))
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAME_COUNT)
    parser.add_argument("--split", choices=("train", "held_out", "all"), default="all")
    args = parser.parse_args()

    if not ffmpeg_available():
        parser.error("ffmpeg is not on PATH. Install it before running extraction.")
    if not args.manifest.is_file():
        parser.error(f"{args.manifest} not found. Run build_manifest.py first.")

    rows = read_manifest(args.manifest)
    if args.split != "all":
        rows = [row for row in rows if row.split == args.split]

    audio_dir = args.out / "audio"
    frame_dir = args.out / "frames"

    extracted = skipped = 0
    failures: list[str] = []

    for index, row in enumerate(rows, start=1):
        source = Path(row.path)
        if (audio_dir / f"{source.stem}.wav").exists() and (frame_dir / source.stem).is_dir():
            skipped += 1
            continue
        try:
            extract_clip(source, audio_dir, frame_dir, frame_count=args.frames)
            extracted += 1
        except MediaExtractionError as error:
            failures.append(str(error))

        if index % 50 == 0:
            print(f"  {index}/{len(rows)} clips processed", flush=True)

    print(f"\nExtracted {extracted}, skipped {skipped} already present, {len(failures)} failed.")
    for failure in failures:
        print(f"  ! {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

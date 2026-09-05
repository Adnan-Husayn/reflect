"""Step 1 — turn an extracted RAVDESS tree into a split manifest.

    python scripts/build_manifest.py --root data/raw --out data/manifest.csv

Reads nothing but filenames, so it runs in seconds and is the right place to
catch a bad download before spending hours on extraction.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravdess.manifest import (
    DEFAULT_HELD_OUT_ACTORS,
    assert_actor_disjoint,
    build_manifest,
    discover_clips,
    summarize,
    write_manifest,
    write_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, required=True, help="Directory holding the extracted RAVDESS files."
    )
    parser.add_argument("--out", type=Path, default=Path("data/manifest.csv"), help="Manifest CSV to write.")
    parser.add_argument(
        "--held-out-actors",
        type=int,
        nargs="+",
        default=list(DEFAULT_HELD_OUT_ACTORS),
        help="Actors reserved for the held-out split. Must not overlap the rest.",
    )
    parser.add_argument(
        "--calm",
        choices=("neutral", "drop"),
        default="neutral",
        help="What to do with the 'calm' class, which has no canonical equivalent.",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        parser.error(f"{args.root} is not a directory.")

    clips = list(discover_clips(args.root, calm_policy=args.calm))
    if not clips:
        parser.error(f"No full audio-video speech clips found under {args.root}.")

    rows = build_manifest(clips, held_out_actors=args.held_out_actors)
    assert_actor_disjoint(rows)

    write_manifest(rows, args.out)
    summary = summarize(rows)
    write_summary(summary, args.out.with_suffix(".summary.json"))

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Step 4 — turn scores.jsonl into the numbers that go in the report and config.

    python scripts/report.py --scores data/scores.jsonl --out results/

DELIBERATELY UNFINISHED. The plumbing either side of this is written; the
analysis is the actual M2 work and belongs to whoever owns the milestone. Each
function below states exactly what it must return and what the result is used
for, so the contract is fixed even though the body is not.

Everything here reads the HELD-OUT split only. Reporting a number computed on
actors the models were fitted on is the one mistake that invalidates the rest.

Four outputs, in dependency order:

    1. per_modality_metrics  -> results/metrics.json, three confusion matrices
    2. fusion_weights        -> backend/app/config.py fusion_weight_*
    3. conflict_threshold    -> backend/app/config.py conflict_threshold
    4. fusion_comparison     -> the report's central claim, or its refutation
"""

import argparse
import json
from pathlib import Path
from typing import Any

CHANNELS = ("text", "voice", "face")


def load_scores(path: Path, split: str = "held_out") -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    return [record for record in records if record["split"] == split]


def per_modality_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Accuracy, macro precision/recall/F1 and a confusion matrix per channel.

    For each of text, voice and face: compare the predicted argmax label against
    the channel's ground truth in `record["truth"]`, over the seven canonical
    emotions. Skip records where that channel is null and report how many were
    skipped -- a channel that failed on 30% of clips has not earned the accuracy
    it reports on the remaining 70%.

    sklearn.metrics.classification_report and confusion_matrix do the work.
    Save each matrix as a figure; the report needs all three.

    Note before writing this: the text channel's truth is "neutral" on every
    clip, so its accuracy is not comparable to the other two and must not be
    read as "the text model is worse". Say so in the report.

    Returns {channel: {"accuracy", "macro_f1", "per_class": {...},
                       "confusion": [[...]], "n", "skipped"}}
    """
    raise NotImplementedError


def fusion_weights(metrics: dict[str, Any]) -> dict[str, float]:
    """Turn measured per-channel reliability into the three fusion weights.

    Any monotone function of reliability is defensible as long as it is stated.
    The straightforward choice is macro-F1 normalized to sum to one; inverse
    error rate is the other common option. Pick one, write down why, and do not
    hand-adjust the result afterwards.

    Excluding the text channel from the weighting is a legitimate choice here,
    given its degenerate ground truth -- but it must be an argued choice in the
    report, not a silent one.

    Returns {"text": w, "voice": w, "face": w}, summing to 1.0, ready to paste
    into backend/app/config.py.
    """
    raise NotImplementedError


def conflict_threshold(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the conflict threshold from labelled disagreement.

    This is the point of using RAVDESS. Every record already carries
    `is_conflict`: True whenever the performed emotion is not neutral, because
    the spoken sentence is emotionally inert while the voice and face are not.

    Take `record["fusion"]["max_divergence"]` as the score and `is_conflict` as
    the binary target, then sklearn.metrics.roc_curve and roc_auc_score give the
    curve. Choose the operating point deliberately rather than by Youden's J
    alone -- decide first whether a false "these channels disagree" or a missed
    disagreement is worse for this application, and say which you chose.

    Report the AUC even if it disappoints. An AUC near 0.5 would mean divergence
    does not separate conflict from agreement at all, which is a real finding
    about the method and is worth more than a threshold quietly tuned to look
    good.

    Returns {"auc", "threshold", "tpr_at_threshold", "fpr_at_threshold",
             "operating_point_rationale", "curve": {"fpr": [...], "tpr": [...]}}
    """
    raise NotImplementedError


def fusion_comparison(records: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, Any]:
    """Does fusion actually beat the best single channel?

    Compare fused accuracy and macro-F1 against each channel alone, on the same
    held-out clips, against the performed-emotion truth. Break the result down
    by intensity ("normal" vs "strong") -- fusion plausibly helps most where a
    single channel is weakest, and that breakdown is more interesting than the
    headline number.

    A negative result is a legitimate finding, and a measured one is worth far
    more than an unmeasured claim. Plan to report it either way.

    Returns {"fused": {...}, "per_channel": {...}, "by_intensity": {...},
             "verdict": str}
    """
    raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scores", type=Path, default=Path("data/scores.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--split", default="held_out")
    args = parser.parse_args()

    records = load_scores(args.scores, split=args.split)
    print(f"Loaded {len(records)} {args.split} records.")

    args.out.mkdir(parents=True, exist_ok=True)

    metrics = per_modality_metrics(records)
    weights = fusion_weights(metrics)
    threshold = conflict_threshold(records)
    comparison = fusion_comparison(records, weights)

    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (args.out / "config_values.json").write_text(
        json.dumps({"fusion_weights": weights, "conflict_threshold": threshold["threshold"]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (args.out / "threshold.json").write_text(json.dumps(threshold, indent=2) + "\n", encoding="utf-8")
    (args.out / "fusion_comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Wrote results to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

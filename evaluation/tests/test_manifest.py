from dataclasses import replace

import pytest

from ravdess.filenames import parse_filename
from ravdess.manifest import (
    assert_actor_disjoint,
    build_manifest,
    read_manifest,
    summarize,
    write_manifest,
)


def clips_for(actors, emotion="05"):
    return [parse_filename(f"01-01-{emotion}-01-01-01-{actor:02d}.mp4") for actor in actors]


def test_held_out_actors_land_in_the_held_out_split():
    rows = build_manifest(clips_for(range(1, 25)), held_out_actors=[19, 20, 21, 22, 23, 24])

    held_out = {row.actor for row in rows if row.split == "held_out"}
    train = {row.actor for row in rows if row.split == "train"}

    assert held_out == {19, 20, 21, 22, 23, 24}
    assert train == set(range(1, 19))


def test_no_actor_appears_in_both_splits():
    rows = build_manifest(clips_for(range(1, 25)))

    assert_actor_disjoint(rows)


def test_a_leaked_actor_is_caught():
    """The check has to fail when one actor's clips straddle the split."""
    rows = build_manifest(clips_for(range(1, 25)))
    # Actor 19 is held out; add a copy of their clip to the training side.
    leaked = [*rows, *(replace(row, split="train") for row in rows if row.actor == 19)]

    with pytest.raises(AssertionError, match="both splits"):
        assert_actor_disjoint(leaked)


def test_the_default_split_is_sex_balanced():
    rows = build_manifest(clips_for(range(1, 25)))
    held_out = {row.actor_sex for row in rows if row.split == "held_out"}
    sexes = [row.actor_sex for row in rows if row.split == "held_out"]

    assert held_out == {"male", "female"}
    assert sexes.count("male") == sexes.count("female")


def test_text_truth_is_neutral_while_voice_and_face_carry_the_emotion():
    (row,) = build_manifest(clips_for([1], emotion="04"))

    assert row.voice_label == "sadness"
    assert row.face_label == "sadness"
    assert row.text_label == "neutral"
    assert row.is_conflict is True


def test_holding_out_nobody_is_rejected():
    with pytest.raises(ValueError, match="At least one actor"):
        build_manifest(clips_for(range(1, 25)), held_out_actors=[])


def test_holding_out_everybody_is_rejected():
    with pytest.raises(ValueError, match="nothing to fit on"):
        build_manifest(clips_for(range(1, 25)), held_out_actors=list(range(1, 25)))


def test_summary_counts_both_splits():
    summary = summarize(build_manifest(clips_for(range(1, 25))))

    assert summary["clips"] == 24
    assert summary["per_split"] == {"train": 18, "held_out": 6}


def test_manifest_survives_a_round_trip(tmp_path):
    rows = build_manifest(clips_for(range(1, 25)))
    destination = tmp_path / "manifest.csv"

    write_manifest(rows, destination)

    assert read_manifest(destination) == rows

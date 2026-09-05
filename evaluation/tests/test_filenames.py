import pytest

from ravdess.filenames import RavdessFilenameError, parse_filename


def test_parses_every_field():
    clip = parse_filename("01-01-05-02-01-02-14.mp4")

    assert clip.modality == "full_av"
    assert clip.vocal_channel == "speech"
    assert clip.emotion == "anger"
    assert clip.intensity == "strong"
    assert clip.statement_text == "Kids are talking by the door"
    assert clip.repetition == 2
    assert clip.actor == 14
    assert clip.actor_sex == "female"


def test_odd_actors_are_male():
    assert parse_filename("01-01-03-01-01-01-13.mp4").actor_sex == "male"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("01", "neutral"),
        ("03", "joy"),
        ("04", "sadness"),
        ("05", "anger"),
        ("06", "fear"),
        ("07", "disgust"),
        ("08", "surprise"),
    ],
)
def test_emotion_codes_map_onto_the_canonical_labels(code, expected):
    assert parse_filename(f"01-01-{code}-01-01-01-01.mp4").emotion == expected


def test_calm_merges_into_neutral_by_default():
    assert parse_filename("01-01-02-01-01-01-01.mp4").emotion == "neutral"


def test_calm_can_be_dropped_instead():
    assert parse_filename("01-01-02-01-01-01-01.mp4", calm_policy="drop") is None


def test_text_ground_truth_is_neutral_even_when_the_performance_is_not():
    clip = parse_filename("01-01-05-02-01-01-07.mp4")

    assert clip.emotion == "anger"
    assert clip.text_label == "neutral"
    assert clip.is_conflict is True


def test_neutral_clips_are_not_conflicts():
    assert parse_filename("01-01-01-01-01-01-07.mp4").is_conflict is False


@pytest.mark.parametrize(
    "name",
    [
        "01-01-05-02-01-02.mp4",  # six fields
        "01-01-05-02-01-02-14-03.mp4",  # eight fields
        "01-01-99-02-01-02-14.mp4",  # unknown emotion
        "09-01-05-02-01-02-14.mp4",  # unknown modality
        "01-01-05-02-01-02-31.mp4",  # actor out of range
    ],
)
def test_malformed_filenames_raise(name):
    with pytest.raises(RavdessFilenameError):
        parse_filename(name)


def test_unknown_calm_policy_is_rejected():
    with pytest.raises(ValueError, match="calm_policy"):
        parse_filename("01-01-02-01-01-01-01.mp4", calm_policy="keep")

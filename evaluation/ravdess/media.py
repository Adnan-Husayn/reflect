"""Split each RAVDESS clip into the inputs the three API endpoints expect.

One `.mp4` carries both channels we need to measure, which is the reason for
using the full audio-video speech set rather than three unrelated corpora:
voice and face are observed on the *same* labelled instant, so fusion can be
evaluated at all.

Audio is written as 16 kHz mono WAV because that is what the Wav2Vec2 checkpoint
resamples to anyway; doing it once here keeps it out of every scoring run.

Frames are sampled from the middle of the clip rather than the whole of it.
RAVDESS recordings open and close on a near-neutral face, so frames taken at the
very start or end are labelled with an emotion that is not yet on the actor's
face. Five frames across the middle also mirrors the live session's own
five-frame smoothing window, which keeps the measurement close to what the
running app actually does.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2

TARGET_SAMPLE_RATE = 16_000
DEFAULT_FRAME_COUNT = 5
# Fraction of the clip to sample frames from, avoiding the neutral lead-in and
# tail. 0.2-0.8 keeps the sampled window inside the performed expression.
DEFAULT_WINDOW = (0.2, 0.8)


class MediaExtractionError(RuntimeError):
    """Raised when ffmpeg or OpenCV cannot read a clip."""


@dataclass(frozen=True, slots=True)
class ExtractedClip:
    """Where the per-channel inputs for one clip ended up on disk."""

    source: Path
    audio: Path
    frames: tuple[Path, ...]


def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def extract_audio(source: Path, destination: Path, sample_rate: int = TARGET_SAMPLE_RATE) -> Path:
    """Write the clip's audio track as mono WAV at the model's sample rate."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "wav",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaExtractionError(f"ffmpeg failed on {source.name}: {result.stderr.strip()}")
    return destination


def extract_frames(
    source: Path,
    destination_dir: Path,
    count: int = DEFAULT_FRAME_COUNT,
    window: tuple[float, float] = DEFAULT_WINDOW,
) -> tuple[Path, ...]:
    """Sample `count` evenly spaced frames from the middle of the clip."""
    start_fraction, end_fraction = window
    if not 0.0 <= start_fraction < end_fraction <= 1.0:
        raise ValueError("window must be an increasing pair inside [0, 1].")
    if count < 1:
        raise ValueError("count must be at least 1.")

    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise MediaExtractionError(f"OpenCV could not open {source.name}.")

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            raise MediaExtractionError(f"{source.name} reports no frames.")

        first = int(total_frames * start_fraction)
        last = int(total_frames * end_fraction) - 1
        if last <= first:
            first, last = 0, total_frames - 1

        step = (last - first) / max(count - 1, 1)
        indices = [first] if count == 1 else [round(first + step * i) for i in range(count)]

        destination_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for position, index in enumerate(indices):
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                # A clip short enough to run out mid-window still yields the
                # frames we did read; a clip that yields none fails below.
                continue
            frame_path = destination_dir / f"{source.stem}_f{position:02d}.jpg"
            if not cv2.imwrite(str(frame_path), frame):
                raise MediaExtractionError(f"Could not write {frame_path}.")
            written.append(frame_path)

        if not written:
            raise MediaExtractionError(f"No frames could be read from {source.name}.")
        return tuple(written)
    finally:
        capture.release()


def extract_clip(
    source: Path,
    audio_dir: Path,
    frame_dir: Path,
    frame_count: int = DEFAULT_FRAME_COUNT,
) -> ExtractedClip:
    """Produce both channel inputs for one clip."""
    audio = extract_audio(source, audio_dir / f"{source.stem}.wav")
    frames = extract_frames(source, frame_dir / source.stem, count=frame_count)
    return ExtractedClip(source=source, audio=audio, frames=frames)

import numpy as np
from faster_whisper import WhisperModel


class SpeechTranscriptionModel:
    """CPU-friendly English transcription for short, live microphone segments."""

    def __init__(self) -> None:
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8")

    def transcribe(self, waveform: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            waveform,
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

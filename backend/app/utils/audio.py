import tempfile
from io import BytesIO

import librosa
import numpy as np


def decode_audio(audio_bytes: bytes) -> np.ndarray:
    """Decode in memory where possible, with a short-lived file fallback for WebM."""
    try:
        waveform, _ = librosa.load(BytesIO(audio_bytes), sr=16_000, mono=True)
    except Exception:
        # Librosa's audioread backend can handle browser WebM recordings by path.
        # The file is removed as soon as decoding completes.
        with tempfile.NamedTemporaryFile(suffix=".webm") as temporary_audio:
            temporary_audio.write(audio_bytes)
            temporary_audio.flush()
            waveform, _ = librosa.load(temporary_audio.name, sr=16_000, mono=True)

    if waveform.size == 0:
        raise ValueError("The uploaded audio contains no samples.")
    return np.asarray(waveform, dtype=np.float32)

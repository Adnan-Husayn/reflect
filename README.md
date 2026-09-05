# Reflect (PCS26/146) — Multimodal Emotion and Mental Health Analytics Using AI

[![CI](https://github.com/Adnan-Husayn/reflect/actions/workflows/ci.yml/badge.svg)](https://github.com/Adnan-Husayn/reflect/actions/workflows/ci.yml)

## v0.3: live session with late fusion and cross-channel conflict detection

This B.Tech project MVP provides a live, conversation-style analysis session. It transcribes short spoken-English segments locally and returns indicators for spoken words, vocal expression, and visible facial expression.

Those channels are fused into a single labelled reading, and **the individual channel scores are always shown alongside it** — never a bare composite number. Disagreement between the channels attenuates the fused confidence, so a reading built from channels that contradict each other is reported as low confidence rather than as a confident label.

The UI describes the output as a model confidence, not a statement of a person's internal emotional state. It is an emotion indicator, not a medical diagnosis.

## Scope

Implemented:

- Local English speech transcription from short microphone segments
- Browser microphone and webcam session with no image uploads or capture button
- Live transcript-text, vocal-expression, and visible-expression indicators
- Five-frame facial-score smoothing and independent partial-failure handling
- Collapsed typed-text fallback for accessibility and testing
- A shared response schema and canonical emotion labels
- Weighted late fusion with the per-channel components always visible
- Cross-channel divergence scoring, used both to flag conflict and to attenuate fused confidence

Planned for later milestones:

- Empirically derived fusion weights and conflict threshold, replacing the provisional defaults
- Quantitative per-modality evaluation, temporal analysis, and calibration
- Carefully scoped mental-health-related indicators

This version intentionally has no persistence, database, authentication, result history, risk score, diagnosis, or treatment recommendation.

## Architecture

```text
React browser live session
  ├── 5-second microphone segment ── POST /predict/live/audio ─┐
  │     └── local English transcript ───────────────────────────┼── FastAPI model wrappers ── independent indicators
  ├── 2-second camera frame ──────── POST /predict/facial ──────┤
  └── optional typed fallback ─────── POST /predict/text ───────┘
                                                                │
  latest score vector per channel ── POST /analyze/fusion ──────┘
```

The frontend requests audio and camera permissions independently. A denied or unavailable modality does not stop the other live indicators.

All API responses normalize model labels to:

```text
anger, disgust, fear, joy, neutral, sadness, surprise
```

## Technologies

- Frontend: React, Vite, TypeScript, Tailwind CSS, browser MediaRecorder and camera APIs
- Backend: FastAPI, Pydantic, PyTorch, Transformers, faster-whisper, Librosa, OpenCV, Pillow
- Local development: Docker Compose or separate local frontend/backend processes

## Pretrained model provenance

The team built the application architecture, processing pipeline, API, interface, and integration. The foundation models below are externally published pretrained checkpoints; they were not trained from scratch by this project.

| Modality | Checkpoint | Purpose |
| --- | --- | --- |
| Text | [`j-hartmann/emotion-english-distilroberta-base`](https://huggingface.co/j-hartmann/emotion-english-distilroberta-base) | Seven-class English DistilRoBERTa emotion classifier |
| Audio | [`superb/wav2vec2-base-superb-er`](https://huggingface.co/superb/wav2vec2-base-superb-er) | Wav2Vec2 speech emotion-recognition checkpoint; input is resampled to 16 kHz |
| Speech transcription | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) `base.en` | Local CPU-int8 English speech transcription |
| Facial | [`dima806/facial_emotions_image_detection`](https://huggingface.co/dima806/facial_emotions_image_detection) | Facial-expression classification candidate with canonical-label normalization |

Please consult each model card for the original authors, licenses, datasets, intended-use notes, and citation guidance before publication or deployment.

## Quick start with Docker

1. Create local environment files:

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. Start the application:

   ```bash
   docker-compose up --build
   ```

The first start downloads the model weights into the Docker-managed `hf-cache` volume. Open:

- Frontend: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps plus pytest and ruff
cp .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

`VITE_API_BASE_URL` sets the frontend API location. `FRONTEND_ORIGIN` sets the FastAPI development CORS origin.

## API

### `GET /health`

Reports whether each model loaded. If one checkpoint cannot load, the status is `degraded`; the remaining modalities still work.

### `POST /predict/text`

```json
{ "text": "I am really happy today." }
```

### `POST /predict/live/audio`

Send one complete multipart WebM/WAV segment in field `file`. The API processes it in memory and returns the local transcript plus separate voice and transcript-text predictions:

```json
{
  "transcript": "I feel calmer today.",
  "audio_prediction": { "label": "neutral", "confidence": 0.7, "scores": {} },
  "text_prediction": { "label": "joy", "confidence": 0.6, "scores": {} }
}
```

### `POST /predict/audio`

Scores one complete audio file without transcribing it. The live session does not call this; it exists as the batch entry point for offline evaluation over a labelled audio set.

### `POST /predict/facial`

Send a multipart form upload in field `file`. JPEG, PNG, and WebP are accepted up to 5 MB. The largest face is selected; no face returns a clear `400` response.

Each prediction endpoint returns:

```json
{
  "label": "joy",
  "confidence": 0.87,
  "scores": {
    "anger": 0.01,
    "disgust": 0.01,
    "fear": 0.02,
    "joy": 0.87,
    "neutral": 0.04,
    "sadness": 0.02,
    "surprise": 0.03
  }
}
```

### `POST /analyze/fusion`

Fuses the latest reading from each channel and measures their disagreement in one pass. Stateless: the client holds the latest reading per channel and sends them together, so no session data is retained.

```json
{
  "text":  { "joy": 0.9, "neutral": 0.1 },
  "voice": { "sadness": 0.8, "neutral": 0.2 },
  "face":  { "sadness": 0.85, "neutral": 0.15 }
}
```

Any subset of `text`, `voice` and `face` is accepted. A single channel still fuses (to itself, unattenuated); fewer than two returns `status: "insufficient_channels"` for the conflict block rather than a misleading zero.

```json
{
  "fused": {
    "label": "sadness",
    "confidence": 0.067,
    "raw_confidence": 0.550,
    "attenuation": 0.121,
    "scores": { "sadness": 0.55, "joy": 0.30, "neutral": 0.15, "...": 0.0 },
    "weights": { "text": 0.333, "voice": 0.333, "face": 0.333 }
  },
  "channels": {
    "text":  { "joy": 0.9, "neutral": 0.1, "...": 0.0 },
    "voice": { "sadness": 0.8, "neutral": 0.2, "...": 0.0 },
    "face":  { "sadness": 0.85, "neutral": 0.15, "...": 0.0 }
  },
  "conflict": {
    "status": "conflict",
    "max_divergence": 0.879,
    "most_divergent_pair": ["face", "text"],
    "threshold": 0.35,
    "conflict_detected": true
  }
}
```

**Fusion and conflict are one engine, not two features.** `confidence` is the value to display; it is `raw_confidence × attenuation`, where `attenuation = 1 − max_divergence`. Channels that agree pass their confidence through almost unchanged; channels that contradict each other drive it toward zero. A naive weighted average would report the example above as sadness at 0.55 — coupling the two makes the composite honest instead.

Because attenuation is continuous rather than thresholded, confidence degrades gracefully even when the binary conflict flag does not fire.

`channels` echoes each input back so the interface can always render the components beside the fused headline.

Divergence is Jensen-Shannon with a base-2 logarithm, so it is bounded to `[0, 1]`: 0 means the channels agree exactly, 1 means they share no probability mass. That bound is what lets the same number serve as both the conflict measure and the attenuation factor. Cosine distance is reported per pair as a baseline for comparison.

A conflict means the channels disagree. It is **not** evidence that a person is concealing an emotion, and it is not a diagnosis.

**Both the `conflict_threshold` of 0.35 and the equal fusion weights are provisional.** The threshold separates strong conflicts from normal variation but misses subtler disagreement, and equal weights assume every modality is equally reliable, which is certainly false. Derive both from held-out labelled data — RAVDESS holds emotion constant across a fixed neutral sentence, which makes it well suited to deriving the threshold — before publishing any accuracy claim.

## Limitations and privacy

This MVP is designed for controlled academic demonstration. It does not provide clinical assessment, therapeutic advice, or generated therapist replies, and should not be used to make medical, employment, safety, or high-impact decisions. Audio segments, camera frames, and transcripts are processed in request memory or short-lived temporary storage only; the application does not save user inputs or add analytics/telemetry.

Facial output is a visible-expression indicator, not a measurement of a person's internal emotion. It may be inaccurate in poor lighting, with occlusion, profile angles, or outside its training conditions. The English transcription model is local and intentionally limited to English in this release.

## Testing

Both suites run in CI on every push and pull request.

Backend — 37 tests, from `backend/`:

```bash
pytest
ruff check .
ruff format --check .
```

Frontend — 26 tests, from `frontend/`:

```bash
npm test
npm run typecheck
npm run test:coverage
```

The backend suite substitutes fake models, so it needs no checkpoint downloads and runs in a few seconds.

Still to check by hand, since they need real devices: microphone-only, camera-only, and combined permission flows; live transcript updates; End session cleanup; no-face handling; stale-request protection; and the typed-text fallback.

See [evaluation/README.md](evaluation/README.md) for a lightweight path to later independent-modality evaluation.

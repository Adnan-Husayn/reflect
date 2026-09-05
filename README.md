# Reflect (PCS26/146) — Multimodal Emotion and Mental Health Analytics Using AI

[![CI](https://github.com/Adnan-Husayn/reflect/actions/workflows/ci.yml/badge.svg)](https://github.com/Adnan-Husayn/reflect/actions/workflows/ci.yml)

## v0.5: trends over recorded sessions

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
- A fused headline in the live session, shown above the three channels and never instead of them
- Session recording for derived score vectors, with per-session and full-withdrawal deletion
- A trends view: mood valence, cross-channel conflict and channel coverage over time
- Optional PHQ-8 / GAD-7 self-report check-ins
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
- Persistence: SQLAlchemy and Alembic. Postgres in Docker and CI; SQLite by default locally, so development and the unit suite need no running services
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
alembic upgrade head                  # creates the schema and seeds the local user
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

### Session persistence

The prediction endpoints stay pure — they persist nothing. Sessions are written
through a separate router, so the evaluation harness can drive `/predict/*`
1,440 times per run without forging a thousand sessions of fake history.

| Endpoint | Purpose |
| --- | --- |
| `POST /sessions` | Open a session, returns its id |
| `POST /sessions/{id}/readings` | Append a batch of derived readings |
| `POST /sessions/{id}/end` | Close the session and compute its rollup |
| `GET /sessions` | List sessions with summaries |
| `GET /sessions/{id}` | One session, its summary and readings |
| `DELETE /sessions/{id}` | Erase one session and everything derived from it |
| `DELETE /users/me/data` | Erase every session, reading and check-in |
| `POST /checkins` | Record one PHQ-8 / GAD-7 self-report |
| `GET /checkins` | List check-ins |
| `GET /trends` | Daily buckets over the recorded sessions |

Readings are posted in batches: a live session emits a facial reading every two
seconds and an audio segment every five, so one request per reading would triple
the request volume for no benefit.

Posting readings to an ended session returns `409`, as does ending one twice.

**`mean_valence` is computed over fused readings only.** Averaging the
per-channel readings instead would let the facial channel dominate — it samples
every 2s against the audio channel's 5s, so its readings outnumber them roughly
2.5 to 1, and the mean would track the sampling rate rather than the mood.
Valence uses the whole score vector rather than the argmax, so a reading that is
0.5 sadness and 0.4 joy is not recorded as if it were purely sad. Surprise sits
at zero because its valence is genuinely ambiguous; the constant is named in
`app/utils/valence.py` so it can be revisited when the distress construct is
defined.

`channel_counts` holds reading counts per channel rather than proportions: the
question it answers is whether a channel was available at all — a denied camera
shows as no face readings — and proportions would merely restate the sampling
rates.

Authentication is not implemented yet. The initial migration seeds one local
user and every session attaches to it, but `user_id` is present from that first
migration and every session-scoped query already filters on it, so real accounts
are a change to how the user is resolved rather than a schema migration.

### `GET /trends`

Daily buckets over completed sessions, with the aggregation done on the server. The valence definition lives in `app/utils/valence.py`; a second implementation in the browser would drift from it, and the definition of the tracked construct has to stay in one file.

Three rules stop the charts lying about sparse days. A day holding one 30-second session and a day holding four 20-minute ones are not comparable, and a naive daily mean draws them at the same weight — so one bad frame on a quiet Tuesday would show up as a visible dip in someone's mood trend.

- **Daily means are weighted by fused-reading count**, not by session, so a long session counts for more than a short one.
- **Every bucket carries `n_sessions` and `n_fused_readings`**, and the interface shows them beside the value in the tooltip.
- **A day below `MINIMUM_READINGS_PER_DAY` returns `null`, not a number**, so the chart draws a gap. Null rather than zero: zero would read as neutral mood.

The rolling window weights across the whole trailing period rather than averaging daily means, so a thin-but-sufficient day does not count as much as a heavy one, and gap days contribute nothing. Sessions that are still open have no rollup and are excluded.

The response carries `minimum_readings_per_day` and `rolling_window_days` so the interface can state the rules it is drawing under rather than hardcoding numbers that would drift.

**Every chart says what it is computed from, on screen**, next to the chart rather than only in the report. Mood valence is a weighted mean over fused readings using the valence map where joy is +1; anger, disgust, fear and sadness are −1; and neutral and surprise are 0. A reader who cannot see that has been handed a number they cannot evaluate.

## Limitations and privacy

This MVP is designed for controlled academic demonstration. It does not provide clinical assessment, therapeutic advice, or generated therapist replies, and should not be used to make medical, employment, safety, or high-impact decisions.

**What is never stored.** Audio segments, camera frames and transcripts are processed in request memory or short-lived temporary storage only. They are never written to the database. The prediction endpoints persist nothing at all, and the persistence API has no multipart endpoint and no bytes-typed column anywhere in its schema, so it cannot store media regardless of what a caller sends. `backend/tests/test_no_media_persisted.py` asserts this by introspecting every column, and reading schemas set `extra="forbid"` so an unexpected `transcript` field is a 422 rather than something silently accepted.

**What is stored, once a session is opened.** Derived score vectors, labels, confidences, the fused reading and its divergence, plus timestamps and a session rollup. Because transcripts are not kept, session replay shows emotion trajectories but never the words spoken. That is the intended trade.

The live session now records automatically. Readings are buffered in the browser and flushed every 15 seconds and again at session end, so a crashed tab loses at most fifteen seconds rather than the whole session. The facial reading written is the smoothed five-frame value the interface actually displayed, not the raw per-frame score — trends therefore inherit that smoothing, and per-frame variance is not recoverable.

**Recording never blocks the session.** If the database is unreachable the live indicators keep working, a quiet "Not recording" badge appears beside the session status, and nothing is written. A failed flush drops its batch rather than retrying: an ever-growing retry queue in a long session is a worse failure than a gap.

**Withdrawal.** `DELETE /sessions/{id}` erases one session and everything derived from it; `DELETE /users/me/data` erases every session, reading and check-in for the user. Both delete rows outright rather than marking them inactive, and both return a receipt of what was removed.

No analytics or telemetry are collected.

Facial output is a visible-expression indicator, not a measurement of a person's internal emotion. It may be inaccurate in poor lighting, with occlusion, profile angles, or outside its training conditions. The English transcription model is local and intentionally limited to English in this release.

## Testing

Both suites run in CI on every push and pull request.

Backend — 90 tests, from `backend/`:

```bash
pytest
ruff check .
ruff format --check .
```

Frontend — 77 tests, from `frontend/`:

```bash
npm test
npm run typecheck
npm run test:coverage
```

The backend suite substitutes fake models, so it needs no checkpoint downloads and runs in a few seconds.

Still to check by hand, since they need real devices: microphone-only, camera-only, and combined permission flows; live transcript updates; End session cleanup; no-face handling; stale-request protection; and the typed-text fallback.

See [evaluation/README.md](evaluation/README.md) for a lightweight path to later independent-modality evaluation.

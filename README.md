# Reflect (PCS26/146) — Multimodal Emotion and Mental Health Analytics Using AI

## v0.2: live conversation emotion session

This B.Tech project MVP provides a live, conversation-style analysis session. It transcribes short spoken-English segments locally and returns separate indicators for spoken words, vocal expression, and visible facial expression. It does **not** combine these channels into an overall score.

The UI describes the output as a model confidence, not a statement of a person's internal emotional state. It is an emotion indicator, not a medical diagnosis.

## Scope

Implemented in v0.1:

- Local English speech transcription from short microphone segments
- Browser microphone and webcam session with no image uploads or capture button
- Live transcript-text, vocal-expression, and visible-expression indicators
- Five-frame facial-score smoothing and independent partial-failure handling
- Collapsed typed-text fallback for accessibility and testing
- A shared response schema and canonical emotion labels

Planned for later milestones:

- Multimodal fusion, temporal analysis, and evaluation refinement
- Carefully scoped mental-health-related indicators

This version intentionally has no persistence, database, authentication, result history, risk score, diagnosis, or treatment recommendation.

## Architecture

```text
React browser live session
  ├── 5-second microphone segment ── POST /predict/live/audio ─┐
  │     └── local English transcript ───────────────────────────┼── FastAPI model wrappers ── independent indicators
  ├── 2-second camera frame ──────── POST /predict/facial ──────┤
  └── optional typed fallback ─────── POST /predict/text ───────┘
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
pip install -r requirements.txt
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

## Limitations and privacy

This MVP is designed for controlled academic demonstration. It does not provide clinical assessment, therapeutic advice, or generated therapist replies, and should not be used to make medical, employment, safety, or high-impact decisions. Audio segments, camera frames, and transcripts are processed in request memory or short-lived temporary storage only; the application does not save user inputs or add analytics/telemetry.

Facial output is a visible-expression indicator, not a measurement of a person's internal emotion. It may be inaccurate in poor lighting, with occlusion, profile angles, or outside its training conditions. The English transcription model is local and intentionally limited to English in this release.

## Testing

Run the small backend baseline suite from `backend/`:

```bash
pytest
```

For manual frontend checks, test microphone-only, camera-only, and combined permission flows; live transcript updates; End session cleanup; no-face handling; stale-request protection; and typed-text fallback.

See [evaluation/README.md](evaluation/README.md) for a lightweight path to later independent-modality evaluation.

import type {
  Channel,
  EmotionPrediction,
  EmotionScores,
  FusionAnalysis,
  LiveAudioAnalysis,
  ReadingBatch,
  SessionOut,
  SessionSummary,
} from "../types/emotion";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Unable to complete analysis.");
  }
  return response.json() as Promise<T>;
}

export function analyzeText(text: string): Promise<EmotionPrediction> {
  return request("/predict/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

function analyzeUpload<T>(path: string, file: Blob, filename: string): Promise<T> {
  const formData = new FormData();
  formData.append("file", file, filename);
  return request<T>(path, { method: "POST", body: formData });
}

export function analyzeAudio(audio: Blob): Promise<EmotionPrediction> {
  return analyzeUpload("/predict/audio", audio, "recording.webm");
}

export function analyzeLiveAudio(audio: Blob): Promise<LiveAudioAnalysis> {
  return analyzeUpload<LiveAudioAnalysis>("/predict/live/audio", audio, "live-segment.webm");
}

export function analyzeFacial(image: Blob): Promise<EmotionPrediction> {
  return analyzeUpload("/predict/facial", image, "captured-face.jpg");
}

/**
 * Fuse the latest reading from each channel.
 *
 * Deliberately a server call rather than the same maths reimplemented here:
 * M2 derives the fusion weights from held-out data, and a second copy in the
 * browser would drift from `backend/app/config.py` the moment they change.
 */
export function fuseChannels(channels: Partial<Record<Channel, EmotionScores>>): Promise<FusionAnalysis> {
  return request("/analyze/fusion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(channels),
  });
}

export function createSession(): Promise<SessionOut> {
  return request("/sessions", { method: "POST" });
}

export function postReadings(sessionId: string, batch: ReadingBatch): Promise<unknown> {
  return request(`/sessions/${sessionId}/readings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(batch),
  });
}

export function endSession(sessionId: string): Promise<SessionSummary> {
  return request(`/sessions/${sessionId}/end`, { method: "POST" });
}

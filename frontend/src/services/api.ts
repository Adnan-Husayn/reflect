import type { EmotionPrediction, LiveAudioAnalysis } from "../types/emotion";

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

import type {
  Channel,
  EmotionPrediction,
  EmotionScores,
  FusionAnalysis,
  LiveAudioAnalysis,
  ReadingBatch,
  SessionDetail,
  SessionListItem,
  SessionOut,
  SessionSummary,
  TrendsOut,
} from "../types/emotion";
import type {
  Account,
  CheckInIn,
  CheckInOut,
  DeletionReceipt,
  Instrument,
} from "../types/emotion";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Thrown on any 401 so the auth layer can redirect rather than parse messages. */
export class UnauthorizedError extends Error {
  constructor() {
    super("Your session has ended. Please sign in again.");
    this.name = "UnauthorizedError";
  }
}

async function request<T>(path: string, options: RequestInit): Promise<T> {
  // credentials: "include" sends the HttpOnly session cookie. The backend
  // allows exactly frontend_origin — a wildcard is invalid with credentials.
  const response = await fetch(`${API_BASE_URL}${path}`, { credentials: "include", ...options });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Unable to complete analysis.");
  }
  if (response.status === 204) {
    return undefined as T;
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

export function getTrends(days = 30): Promise<TrendsOut> {
  return request(`/trends?days=${days}`, { method: "GET" });
}

export function getSessions(): Promise<SessionListItem[]> {
  return request("/sessions", { method: "GET" });
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}`, { method: "GET" });
}

export function getInstrument(code = "PHQ-8"): Promise<Instrument> {
  return request(`/instruments/${code}`, { method: "GET" });
}

export function postCheckin(checkin: CheckInIn): Promise<CheckInOut> {
  return request("/checkins", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(checkin),
  });
}

export function getCheckins(): Promise<CheckInOut[]> {
  return request("/checkins", { method: "GET" });
}

/** Withdrawal. Deletes rows outright; there is no undo. */
export function deleteMyData(): Promise<DeletionReceipt> {
  return request("/users/me/data", { method: "DELETE" });
}

export function register(email: string, password: string): Promise<Account> {
  return request("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<Account> {
  return request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return request("/auth/logout", { method: "POST" });
}

export function getAccount(): Promise<Account> {
  return request("/auth/me", { method: "GET" });
}

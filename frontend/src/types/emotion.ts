export type EmotionLabel =
  | "anger"
  | "disgust"
  | "fear"
  | "joy"
  | "neutral"
  | "sadness"
  | "surprise";

export type Channel = "text" | "voice" | "face";

export type EmotionScores = Record<EmotionLabel, number>;

export interface EmotionPrediction {
  label: EmotionLabel;
  confidence: number;
  scores: EmotionScores;
}

export interface LiveAudioAnalysis {
  transcript: string;
  audio_prediction: EmotionPrediction | null;
  text_prediction: EmotionPrediction | null;
}

/** Mirrors backend/app/schemas/emotion.py. */
export interface FusedPrediction {
  label: EmotionLabel;
  /** Attenuated by divergence. This is the value to display. */
  confidence: number;
  raw_confidence: number;
  attenuation: number;
  scores: EmotionScores;
  weights: Partial<Record<Channel, number>>;
}

export interface PairDivergence {
  channels: Channel[];
  jensen_shannon: number;
  cosine_distance: number;
}

export interface ConflictAnalysis {
  status: "conflict" | "aligned" | "insufficient_channels";
  channels_compared: Channel[];
  pairs: PairDivergence[];
  max_divergence: number | null;
  mean_divergence: number | null;
  most_divergent_pair: Channel[] | null;
  threshold: number;
  conflict_detected: boolean;
}

export interface FusionAnalysis {
  fused: FusedPrediction | null;
  channels: Partial<Record<Channel, EmotionScores>>;
  conflict: ConflictAnalysis;
}

/** Mirrors backend/app/schemas/session.py. */
export interface ReadingIn {
  t: string;
  channel: Channel;
  label: EmotionLabel;
  confidence: number;
  scores: EmotionScores;
}

export interface FusedReadingIn {
  t: string;
  label: EmotionLabel;
  confidence: number;
  raw_confidence: number;
  attenuation: number;
  max_divergence: number | null;
  conflict: boolean;
  scores: EmotionScores;
}

export interface ReadingBatch {
  readings: ReadingIn[];
  fused: FusedReadingIn[];
}

export interface SessionOut {
  id: string;
  started_at: string;
  ended_at: string | null;
}

export interface SessionSummary {
  session_id: string;
  n_readings: number;
  n_fused_readings: number;
  mean_valence: number | null;
  conflict_rate: number | null;
  dominant_label: EmotionLabel | null;
  channel_counts: Partial<Record<Channel, number>>;
  computed_at: string;
}

/** Mirrors backend/app/schemas/trends.py. */
export interface TrendBucket {
  date: string;
  n_sessions: number;
  n_fused_readings: number;
  /** Null on a day below the reading minimum — draw a gap, never a zero. */
  mean_valence: number | null;
  rolling_valence: number | null;
  conflict_rate: number | null;
  channel_counts: Partial<Record<Channel, number>>;
  sufficient: boolean;
}

export interface TrendsOut {
  start: string;
  end: string;
  buckets: TrendBucket[];
  minimum_readings_per_day: number;
  rolling_window_days: number;
}

export interface SessionListItem extends SessionOut {
  summary: SessionSummary | null;
}

export interface ReadingOut {
  t: string;
  channel: Channel;
  label: EmotionLabel;
  confidence: number;
  scores: EmotionScores;
}

export interface FusedReadingOut {
  t: string;
  label: EmotionLabel;
  confidence: number;
  raw_confidence: number;
  attenuation: number;
  max_divergence: number | null;
  conflict: boolean;
  scores: EmotionScores;
}

export interface SessionDetail extends SessionOut {
  summary: SessionSummary | null;
  readings: ReadingOut[];
  fused_readings: FusedReadingOut[];
}

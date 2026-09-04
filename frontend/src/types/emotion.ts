export type EmotionLabel =
  | "anger"
  | "disgust"
  | "fear"
  | "joy"
  | "neutral"
  | "sadness"
  | "surprise";

export interface EmotionPrediction {
  label: EmotionLabel;
  confidence: number;
  scores: Record<EmotionLabel, number>;
}

export interface LiveAudioAnalysis {
  transcript: string;
  audio_prediction: EmotionPrediction | null;
  text_prediction: EmotionPrediction | null;
}

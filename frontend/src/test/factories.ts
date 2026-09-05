import type { EmotionLabel, EmotionPrediction } from "../types/emotion";

const EMOTIONS: EmotionLabel[] = [
  "anger",
  "disgust",
  "fear",
  "joy",
  "neutral",
  "sadness",
  "surprise",
];

/** Build a full prediction from the named emotions; the rest score zero. */
export function makePrediction(weights: Partial<Record<EmotionLabel, number>>): EmotionPrediction {
  const scores = Object.fromEntries(
    EMOTIONS.map((emotion) => [emotion, weights[emotion] ?? 0]),
  ) as Record<EmotionLabel, number>;
  const label = EMOTIONS.reduce((best, emotion) => (scores[emotion] > scores[best] ? emotion : best), EMOTIONS[0]);
  return { label, confidence: scores[label], scores };
}

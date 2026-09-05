import type { EmotionLabel, EmotionPrediction } from "../types/emotion";

export const EMOTIONS: EmotionLabel[] = [
  "anger",
  "disgust",
  "fear",
  "joy",
  "neutral",
  "sadness",
  "surprise",
];

/** How many recent frames the facial indicator averages over. */
export const FACE_HISTORY_LENGTH = 5;

/**
 * Average a run of predictions into one smoothed prediction.
 *
 * Frame-by-frame facial scores are noisy, so the indicator shows the mean of
 * the recent frames rather than the latest one.
 */
export function averagePredictions(predictions: EmotionPrediction[]): EmotionPrediction {
  if (predictions.length === 0) {
    throw new Error("Cannot average an empty prediction history.");
  }
  const scores = Object.fromEntries(
    EMOTIONS.map((emotion) => [
      emotion,
      predictions.reduce((sum, prediction) => sum + prediction.scores[emotion], 0) / predictions.length,
    ]),
  ) as EmotionPrediction["scores"];
  const label = EMOTIONS.reduce((highest, emotion) => (scores[emotion] > scores[highest] ? emotion : highest), EMOTIONS[0]);
  return { label, confidence: scores[label], scores };
}

/** Append a prediction, keeping only the most recent `FACE_HISTORY_LENGTH` frames. */
export function appendToHistory(
  history: EmotionPrediction[],
  prediction: EmotionPrediction,
): EmotionPrediction[] {
  return [...history.slice(-(FACE_HISTORY_LENGTH - 1)), prediction];
}

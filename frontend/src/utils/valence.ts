import type { EmotionLabel, EmotionScores } from "../types/emotion";

/**
 * Mirrors backend/app/utils/valence.py.
 *
 * Duplicated deliberately and narrowly: this draws a stored series the server
 * has already returned, and asking the server to re-valence readings it just
 * sent would be a request per replay. The map is eight constants and a test
 * pins the same cases the Python suite does — if it ever needs to grow beyond
 * this, it should move back to the server.
 *
 * Surprise sits at zero because its valence is genuinely ambiguous.
 */
export const VALENCE: Record<EmotionLabel, number> = {
  joy: 1,
  anger: -1,
  disgust: -1,
  fear: -1,
  sadness: -1,
  neutral: 0,
  surprise: 0,
};

/** Expected valence of one score vector, in [-1, 1]. Renormalises first. */
export function valenceOf(scores: EmotionScores): number {
  const total = Object.values(scores).reduce((sum, value) => sum + Math.max(value, 0), 0);
  if (total <= 0) return 0;
  return (Object.entries(scores) as [EmotionLabel, number][]).reduce(
    (sum, [emotion, value]) => sum + VALENCE[emotion] * (Math.max(value, 0) / total),
    0,
  );
}

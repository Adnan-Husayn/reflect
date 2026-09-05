import type {
  Channel,
  EmotionLabel,
  EmotionPrediction,
  EmotionScores,
  FusionAnalysis,
} from "../types/emotion";

const EMOTIONS: EmotionLabel[] = [
  "anger",
  "disgust",
  "fear",
  "joy",
  "neutral",
  "sadness",
  "surprise",
];

export function makeScores(weights: Partial<Record<EmotionLabel, number>>): EmotionScores {
  return Object.fromEntries(
    EMOTIONS.map((emotion) => [emotion, weights[emotion] ?? 0]),
  ) as EmotionScores;
}

/** Build a full prediction from the named emotions; the rest score zero. */
export function makePrediction(weights: Partial<Record<EmotionLabel, number>>): EmotionPrediction {
  const scores = makeScores(weights);
  const label = EMOTIONS.reduce((best, emotion) => (scores[emotion] > scores[best] ? emotion : best), EMOTIONS[0]);
  return { label, confidence: scores[label], scores };
}

interface FusionOptions {
  label?: EmotionLabel;
  confidence?: number;
  rawConfidence?: number;
  attenuation?: number;
  maxDivergence?: number | null;
  conflict?: boolean;
  channels?: Channel[];
  pair?: Channel[] | null;
}

export function makeFusion({
  label = "joy",
  confidence = 0.72,
  rawConfidence = 0.8,
  attenuation = 0.9,
  maxDivergence = 0.1,
  conflict = false,
  channels = ["text", "voice", "face"],
  pair = ["face", "text"],
}: FusionOptions = {}): FusionAnalysis {
  return {
    fused: {
      label,
      confidence,
      raw_confidence: rawConfidence,
      attenuation,
      scores: makeScores({ [label]: 1 }),
      weights: Object.fromEntries(channels.map((channel) => [channel, 1 / channels.length])),
    },
    channels: Object.fromEntries(channels.map((channel) => [channel, makeScores({ [label]: 1 })])),
    conflict: {
      status: conflict ? "conflict" : "aligned",
      channels_compared: channels,
      pairs: [
        { channels: ["face", "text"], jensen_shannon: maxDivergence ?? 0, cosine_distance: 0.5 },
        { channels: ["face", "voice"], jensen_shannon: 0.05, cosine_distance: 0.06 },
      ],
      max_divergence: maxDivergence,
      mean_divergence: maxDivergence,
      most_divergent_pair: pair,
      threshold: 0.35,
      conflict_detected: conflict,
    },
  };
}

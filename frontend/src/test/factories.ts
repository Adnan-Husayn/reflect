import type {
  Channel,
  EmotionLabel,
  EmotionPrediction,
  EmotionScores,
  FusionAnalysis,
  Correlation,
  Instrument,
  TrendBucket,
  TrendsOut,
  Wellbeing,
  WellbeingStatus,
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

interface BucketOptions {
  date: string;
  sessions?: number;
  readings?: number;
  valence?: number | null;
  rolling?: number | null;
  conflict?: number | null;
  counts?: Partial<Record<Channel, number>>;
  checkin?: number | null;
}

/** A day below the minimum comes back as a gap: nulls, not zeros. */
export function makeBucket({
  date,
  sessions = 1,
  readings = 60,
  valence = 0.4,
  rolling = 0.35,
  conflict = 0.2,
  counts = { text: 12, voice: 12, face: 30 },
  checkin = null,
}: BucketOptions): TrendBucket {
  const sufficient = readings >= 20;
  return {
    date,
    n_sessions: sessions,
    n_fused_readings: readings,
    mean_valence: sufficient ? valence : null,
    rolling_valence: sufficient ? rolling : null,
    conflict_rate: sufficient ? conflict : null,
    channel_counts: counts,
    sufficient,
    checkin_score: checkin,
  };
}

export function makeTrends(
  buckets: TrendBucket[],
  correlation: Correlation = { r: null, n: 0, minimum_pairs: 4 },
): TrendsOut {
  return {
    start: buckets[0]?.date ?? "2026-09-01",
    end: buckets[buckets.length - 1]?.date ?? "2026-09-01",
    buckets,
    minimum_readings_per_day: 20,
    rolling_window_days: 7,
    correlation,
  };
}

export function makeInstrument(): Instrument {
  return {
    code: "PHQ-8",
    name: "Patient Health Questionnaire-8",
    prompt: "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
    max_score: 24,
    items: Array.from({ length: 8 }, (_, index) => ({
      id: `q${index + 1}`,
      text: `Item ${index + 1}`,
    })),
    options: [
      { value: 0, label: "Not at all" },
      { value: 1, label: "Several days" },
      { value: 2, label: "More than half the days" },
      { value: 3, label: "Nearly every day" },
    ],
  };
}

interface WellbeingOptions {
  status?: WellbeingStatus;
  daysWithData?: number;
  lowValenceDays?: number;
  conflictDays?: number;
  sustainedLowValence?: boolean;
  sustainedConflict?: boolean;
  prompts?: Wellbeing["prompts"];
}

export function makeWellbeing({
  status = "steady",
  daysWithData = 5,
  lowValenceDays = 0,
  conflictDays = 0,
  sustainedLowValence = false,
  sustainedConflict = false,
  prompts = [
    {
      key: "steady",
      observation: "Nothing in this week's readings stood out from your usual range.",
      suggestion: "That is a statement about the readings, not about you.",
    },
  ],
}: WellbeingOptions = {}): Wellbeing {
  return {
    status,
    days_with_data: daysWithData,
    low_valence_days: lowValenceDays,
    conflict_days: conflictDays,
    sustained_low_valence: sustainedLowValence,
    sustained_conflict: sustainedConflict,
    window_days: 7,
    sustained_days_required: 3,
    minimum_days: 3,
    days: Array.from({ length: 7 }, (_, index) => ({
      date: `2026-09-0${index + 1}`,
      n_readings: 40,
      low_valence_share: 0.1,
      conflict_share: 0.1,
      sufficient: true,
    })),
    prompts,
    low_valence_threshold: -0.2,
    low_valence_share_threshold: 0.4,
    conflict_share_threshold: 0.4,
  };
}

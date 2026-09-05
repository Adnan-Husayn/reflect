import { describe, expect, it } from "vitest";
import { FACE_HISTORY_LENGTH, appendToHistory, averagePredictions } from "./smoothing";
import { makePrediction } from "../test/factories";

describe("averagePredictions", () => {
  it("returns the single prediction unchanged", () => {
    const only = makePrediction({ joy: 0.8, neutral: 0.2 });
    expect(averagePredictions([only]).scores).toEqual(only.scores);
  });

  it("averages the scores across frames", () => {
    const result = averagePredictions([
      makePrediction({ joy: 1 }),
      makePrediction({ sadness: 1 }),
    ]);
    expect(result.scores.joy).toBeCloseTo(0.5);
    expect(result.scores.sadness).toBeCloseTo(0.5);
  });

  it("lets a consistent signal outvote a single noisy frame", () => {
    const smoothed = averagePredictions([
      makePrediction({ neutral: 0.9, surprise: 0.1 }),
      makePrediction({ neutral: 0.9, surprise: 0.1 }),
      makePrediction({ surprise: 0.9, neutral: 0.1 }),
    ]);
    expect(smoothed.label).toBe("neutral");
  });

  it("keeps the averaged distribution normalised", () => {
    const smoothed = averagePredictions([
      makePrediction({ joy: 0.6, neutral: 0.4 }),
      makePrediction({ fear: 0.5, anger: 0.5 }),
    ]);
    const total = Object.values(smoothed.scores).reduce((sum, score) => sum + score, 0);
    expect(total).toBeCloseTo(1);
  });

  it("reports the confidence of the winning label", () => {
    const smoothed = averagePredictions([makePrediction({ joy: 0.7, neutral: 0.3 })]);
    expect(smoothed.confidence).toBeCloseTo(smoothed.scores[smoothed.label]);
  });

  it("refuses an empty history rather than returning NaN scores", () => {
    expect(() => averagePredictions([])).toThrow("Cannot average an empty prediction history.");
  });
});

describe("appendToHistory", () => {
  it("keeps at most the configured number of frames", () => {
    let history = [] as ReturnType<typeof makePrediction>[];
    for (let index = 0; index < 12; index += 1) {
      history = appendToHistory(history, makePrediction({ joy: index / 12 }));
    }
    expect(history).toHaveLength(FACE_HISTORY_LENGTH);
  });

  it("drops the oldest frame first", () => {
    let history = [makePrediction({ anger: 1 })];
    for (let index = 0; index < FACE_HISTORY_LENGTH; index += 1) {
      history = appendToHistory(history, makePrediction({ joy: 1 }));
    }
    expect(history.every((prediction) => prediction.label === "joy")).toBe(true);
  });

  it("does not mutate the history it is given", () => {
    const original = [makePrediction({ joy: 1 })];
    const next = appendToHistory(original, makePrediction({ fear: 1 }));
    expect(original).toHaveLength(1);
    expect(next).toHaveLength(2);
  });
});

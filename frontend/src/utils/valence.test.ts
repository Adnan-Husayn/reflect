import { describe, expect, it } from "vitest";
import { VALENCE, valenceOf } from "./valence";
import { makeScores } from "../test/factories";

/* The same cases the Python suite pins, so the two copies cannot drift
   silently. See the note in valence.ts on why this is duplicated. */
describe("valenceOf", () => {
  it("covers every canonical emotion", () => {
    expect(Object.keys(VALENCE).sort()).toEqual([
      "anger",
      "disgust",
      "fear",
      "joy",
      "neutral",
      "sadness",
      "surprise",
    ]);
  });

  it("puts pure joy and pure sadness at the bounds", () => {
    expect(valenceOf(makeScores({ joy: 1 }))).toBeCloseTo(1);
    expect(valenceOf(makeScores({ sadness: 1 }))).toBeCloseTo(-1);
  });

  it("treats neutral and surprise as zero", () => {
    expect(valenceOf(makeScores({ neutral: 1 }))).toBeCloseTo(0);
    expect(valenceOf(makeScores({ surprise: 1 }))).toBeCloseTo(0);
  });

  it("uses the whole vector rather than the argmax", () => {
    expect(valenceOf(makeScores({ sadness: 0.5, joy: 0.4, neutral: 0.1 }))).toBeCloseTo(-0.1);
  });

  it("renormalises raw weights", () => {
    expect(valenceOf(makeScores({ joy: 2, sadness: 2 }))).toBeCloseTo(
      valenceOf(makeScores({ joy: 0.5, sadness: 0.5 })),
    );
  });

  it("returns zero rather than NaN for an empty vector", () => {
    expect(valenceOf(makeScores({}))).toBe(0);
  });
});

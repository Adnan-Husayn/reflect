import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SessionReplay } from "./SessionReplay";
import { makeScores } from "../../test/factories";

function reading(minute: number, weights: Parameters<typeof makeScores>[0], conflict = false) {
  return {
    t: `2026-09-06T12:${String(minute).padStart(2, "0")}:00Z`,
    label: "joy" as const,
    confidence: 0.6,
    raw_confidence: 0.8,
    attenuation: 0.75,
    max_divergence: 0.2,
    conflict,
    scores: makeScores(weights),
  };
}

describe("SessionReplay", () => {
  it("draws the trajectory of the session", () => {
    render(
      <SessionReplay
        fused={[reading(0, { joy: 1 }), reading(5, { sadness: 1 }), reading(10, { neutral: 1 })]}
      />,
    );
    expect(screen.getByRole("heading", { name: "How the session went" })).toBeInTheDocument();
  });

  it("renders nothing when the session recorded nothing", () => {
    const { container } = render(<SessionReplay fused={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("states what the series is computed from", () => {
    render(<SessionReplay fused={[reading(0, { joy: 1 })]} />);
    const caption = screen.getByText(/Each point is one combined reading/);
    expect(caption).toHaveTextContent("joy is +1");
    expect(caption).toHaveTextContent("before it was averaged");
  });

  it("says transcripts are not stored, so replay shows no words", () => {
    render(<SessionReplay fused={[reading(0, { joy: 1 })]} />);
    expect(screen.getByText(/never the words/)).toBeInTheDocument();
  });
});

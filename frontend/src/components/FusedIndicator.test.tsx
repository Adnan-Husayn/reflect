import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FusedIndicator } from "./FusedIndicator";
import { makeFusion } from "../test/factories";

describe("FusedIndicator", () => {
  it("waits before any fused reading has arrived", () => {
    render(<FusedIndicator analysis={null} state="Session not started" />);
    expect(screen.getByText("Session not started")).toBeInTheDocument();
  });

  it("shows the attenuated confidence, never the raw value", () => {
    render(
      <FusedIndicator
        analysis={makeFusion({ label: "sadness", confidence: 0.07, rawConfidence: 0.55 })}
        state="Live"
      />,
    );
    expect(screen.getByText("Sadness")).toBeInTheDocument();
    expect(screen.getByText("7% model confidence")).toBeInTheDocument();
    expect(screen.queryByText("55% model confidence")).not.toBeInTheDocument();
  });

  it("names the disagreeing channels when a conflict is detected", () => {
    render(
      <FusedIndicator
        analysis={makeFusion({
          conflict: true,
          maxDivergence: 0.88,
          pair: ["face", "text"],
          confidence: 0.07,
          rawConfidence: 0.55,
        })}
        state="Live"
      />,
    );
    expect(
      screen.getByText("Visible facial expression and spoken words disagree."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Confidence is reduced from 55% to 7%/)).toBeInTheDocument();
  });

  it("never frames a conflict as concealment", () => {
    render(<FusedIndicator analysis={makeFusion({ conflict: true, maxDivergence: 0.9 })} state="Live" />);
    const caveat = screen.getByText(/A conflict means the channels disagree/);
    expect(caveat).toHaveTextContent("not evidence that a person is concealing an emotion");
    expect(caveat).toHaveTextContent("not a diagnosis");
  });

  it("reports agreement when the channels align", () => {
    const { container } = render(
      <FusedIndicator analysis={makeFusion({ conflict: false, maxDivergence: 0.04 })} state="Live" />,
    );
    expect(screen.getByText(/The channels broadly agree/)).toBeInTheDocument();
    // The caveat paragraph always contains the word "disagree", so assert on
    // the conflict headline itself rather than on the copy.
    expect(container.querySelector(".fused-conflict-headline")).toBeNull();
    expect(container.querySelector(".fused-indicator.conflict")).toBeNull();
  });

  it("plots divergence against the provisional threshold", () => {
    const { container } = render(
      <FusedIndicator analysis={makeFusion({ maxDivergence: 0.62 })} state="Live" />,
    );
    // 0.62 also appears in the pairwise table, so scope to the headline reading.
    expect(container.querySelector(".divergence-reading")).toHaveTextContent(
      "0.62 maximum divergence, against a provisional threshold of 0.35.",
    );
    expect(container.querySelector(".divergence-fill")).toHaveStyle({ width: "62%" });
    expect(container.querySelector(".divergence-threshold")).toHaveStyle({ left: "35%" });
  });

  it("lists the pairwise divergences behind a disclosure", () => {
    render(<FusedIndicator analysis={makeFusion({ maxDivergence: 0.62 })} state="Live" />);
    expect(screen.getByText("View pairwise divergence")).toBeInTheDocument();
    expect(screen.getByText("Visible facial expression → spoken words")).toBeInTheDocument();
  });

  it("says how many channels the reading was built from", () => {
    render(<FusedIndicator analysis={makeFusion({ channels: ["text", "voice"] })} state="Live" />);
    expect(screen.getByText("2 of 3 channels")).toBeInTheDocument();
  });

  it("surfaces an error instead of a stale reading", () => {
    render(
      <FusedIndicator analysis={makeFusion()} state="Live" error="Combined reading is unavailable." />,
    );
    expect(screen.getByText("Combined reading is unavailable.")).toBeInTheDocument();
    expect(screen.queryByText(/model confidence/)).not.toBeInTheDocument();
  });
});

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LiveEmotionIndicator } from "./LiveEmotionIndicator";
import { makePrediction } from "../test/factories";

const base = { title: "Vocal expression", description: "From the latest voice segment" };

describe("LiveEmotionIndicator", () => {
  it("shows the waiting state in both the badge and the body when no prediction has arrived", () => {
    const { container } = render(
      <LiveEmotionIndicator {...base} prediction={null} state="Microphone is off" />,
    );
    expect(container.querySelector(".live-badge")).toHaveTextContent("Microphone is off");
    expect(container.querySelector(".indicator-waiting")).toHaveTextContent("Microphone is off");
    expect(screen.queryByText(/Model confidence/)).not.toBeInTheDocument();
  });

  it("title-cases the label and renders confidence as a whole percentage", () => {
    const { container } = render(
      <LiveEmotionIndicator {...base} prediction={makePrediction({ sadness: 0.874, neutral: 0.126 })} state="Listening" />,
    );
    expect(container.querySelector(".indicator-result strong")).toHaveTextContent("Sadness");
    expect(screen.getByText("Model confidence 87%")).toBeInTheDocument();
  });

  it("labels the channel as live once a prediction exists", () => {
    const { container } = render(
      <LiveEmotionIndicator {...base} prediction={makePrediction({ joy: 1 })} state="Listening" />,
    );
    expect(container.querySelector(".live-badge")).toHaveTextContent("Live");
  });

  it("prefers the error over a stale prediction so a failure is never hidden", () => {
    render(
      <LiveEmotionIndicator
        {...base}
        prediction={makePrediction({ joy: 1 })}
        state="Listening"
        error="Live audio analysis is unavailable."
      />,
    );
    expect(screen.getByText("Live audio analysis is unavailable.")).toBeInTheDocument();
    expect(screen.queryByText(/Model confidence/)).not.toBeInTheDocument();
  });

  it("orders the distribution from most to least likely", () => {
    const { container } = render(
      <LiveEmotionIndicator
        {...base}
        prediction={makePrediction({ joy: 0.5, fear: 0.3, anger: 0.2 })}
        state="Listening"
      />,
    );
    const scoreList = container.querySelector(".score-list") as HTMLElement;
    const rows = within(scoreList)
      .getAllByText(/^(Anger|Disgust|Fear|Joy|Neutral|Sadness|Surprise)$/)
      .map((node) => node.textContent);
    expect(rows.slice(0, 3)).toEqual(["Joy", "Fear", "Anger"]);
  });
});

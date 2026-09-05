import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ValenceTrend } from "./ValenceTrend";
import { makeBucket, makeTrends } from "../../test/factories";

const trends = makeTrends([
  makeBucket({ date: "2026-09-01", readings: 80, valence: 0.5 }),
  makeBucket({ date: "2026-09-02", readings: 3, valence: -1 }),
  makeBucket({ date: "2026-09-03", readings: 90, valence: 0.6 }),
]);

describe("ValenceTrend", () => {
  it("states what the number is computed from, on screen", () => {
    render(<ValenceTrend trends={trends} />);
    const caption = screen.getByText(/Weighted mean over fused readings/);
    expect(caption).toHaveTextContent("joy is +1");
    expect(caption).toHaveTextContent("neutral and surprise are 0");
  });

  it("names the reading minimum and the rolling window it was given", () => {
    render(<ValenceTrend trends={trends} />);
    const caption = screen.getByText(/Weighted mean over fused readings/);
    expect(caption).toHaveTextContent("fewer than 20 fused readings are shown as gaps");
    expect(caption).toHaveTextContent("7-day rolling mean");
  });

  it("leaves a sparse day as a null so the line breaks rather than dipping", () => {
    render(<ValenceTrend trends={trends} />);
    // The middle day fell under the minimum, so the endpoint nulled it.
    expect(trends.buckets[1].mean_valence).toBeNull();
    expect(trends.buckets[1].sufficient).toBe(false);
  });

  it("renders a heading for the chart", () => {
    render(<ValenceTrend trends={trends} />);
    expect(screen.getByRole("heading", { name: "Mood valence" })).toBeInTheDocument();
  });
});

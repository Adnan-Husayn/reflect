import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConflictTrend } from "./ConflictTrend";
import { makeBucket, makeTrends } from "../../test/factories";

const trends = makeTrends([makeBucket({ date: "2026-09-01", conflict: 0.4 })]);

describe("ConflictTrend", () => {
  it("states what the rate is computed from", () => {
    render(<ConflictTrend trends={trends} />);
    expect(screen.getByText(/share of a day's fused readings/)).toBeInTheDocument();
  });

  it("never frames conflict as concealment", () => {
    render(<ConflictTrend trends={trends} />);
    expect(screen.getByText(/not evidence of concealment/)).toBeInTheDocument();
  });

  it("renders a heading for the chart", () => {
    render(<ConflictTrend trends={trends} />);
    expect(screen.getByRole("heading", { name: "Cross-channel conflict" })).toBeInTheDocument();
  });
});

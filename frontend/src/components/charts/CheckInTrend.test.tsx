import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CheckInTrend } from "./CheckInTrend";
import { makeBucket, makeTrends } from "../../test/factories";

const trends = makeTrends([
  makeBucket({ date: "2026-09-01", checkin: 6 }),
  makeBucket({ date: "2026-09-02" }),
]);

describe("CheckInTrend", () => {
  it("states what the score is computed from", () => {
    render(<CheckInTrend trends={trends} />);
    const caption = screen.getByText(/total of the eight PHQ-8 items/);
    expect(caption).toHaveTextContent("recomputed on the server");
    expect(caption).toHaveTextContent("0 to 24");
  });

  it("warns that its scale runs opposite to valence", () => {
    render(<CheckInTrend trends={trends} />);
    expect(screen.getByText(/the opposite direction to valence above/)).toBeInTheDocument();
  });

  it("says no score is graded or categorised", () => {
    render(<CheckInTrend trends={trends} />);
    expect(
      screen.getByText(/No score is graded or mapped onto a severity category/),
    ).toBeInTheDocument();
  });

  it("renders as its own chart rather than a second axis", () => {
    render(<CheckInTrend trends={trends} />);
    expect(screen.getByRole("heading", { name: "PHQ-8 check-in score" })).toBeInTheDocument();
  });
});

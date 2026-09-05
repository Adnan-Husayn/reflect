import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChannelCoverage } from "./ChannelCoverage";
import { makeBucket, makeTrends } from "../../test/factories";

const trends = makeTrends([
  makeBucket({ date: "2026-09-01", counts: { text: 10, voice: 10, face: 25 } }),
]);

describe("ChannelCoverage", () => {
  it("explains that counts are counts, not proportions", () => {
    render(<ChannelCoverage trends={trends} />);
    const caption = screen.getByText(/Reading counts per channel per day/);
    expect(caption).toHaveTextContent("not proportions");
    expect(caption).toHaveTextContent("a denied camera shows as no facial readings");
  });

  it("warns that the sampling rates differ by design", () => {
    render(<ChannelCoverage trends={trends} />);
    expect(screen.getByText(/every 2 seconds against the audio channel's 5/)).toBeInTheDocument();
  });

  it("renders a heading for the chart", () => {
    render(<ChannelCoverage trends={trends} />);
    expect(screen.getByRole("heading", { name: "Channel coverage" })).toBeInTheDocument();
  });
});

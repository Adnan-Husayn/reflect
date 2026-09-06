import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CorrelationNote } from "./CorrelationNote";

describe("CorrelationNote", () => {
  it("withholds the coefficient below the minimum pair count", () => {
    render(<CorrelationNote correlation={{ r: null, n: 2, minimum_pairs: 4 }} />);

    expect(screen.getByText(/2 of the 4 needed/)).toBeInTheDocument();
    expect(screen.queryByText(/^r = /)).not.toBeInTheDocument();
  });

  it("explains what a pair is, so the count is interpretable", () => {
    render(<CorrelationNote correlation={{ r: null, n: 1, minimum_pairs: 4 }} />);
    expect(
      screen.getByText(/a day with both a recorded session and a check-in/),
    ).toBeInTheDocument();
  });

  it("renders r alongside its n", () => {
    render(<CorrelationNote correlation={{ r: -0.62, n: 9, minimum_pairs: 4 }} />);

    expect(screen.getByText("r = -0.62")).toBeInTheDocument();
    expect(screen.getByText("over n = 9 paired days")).toBeInTheDocument();
  });

  it("states which direction would support the hypothesis", () => {
    render(<CorrelationNote correlation={{ r: -0.62, n: 9, minimum_pairs: 4 }} />);
    const caption = screen.getByText(/Pearson correlation between/);
    expect(caption).toHaveTextContent("negative");
    expect(caption).toHaveTextContent("PHQ-8 rises as wellbeing falls");
  });

  it("states its own weakness whether or not a value is shown", () => {
    const { rerender } = render(<CorrelationNote correlation={{ r: -0.62, n: 9, minimum_pairs: 4 }} />);
    expect(screen.getByText(/within-subject correlation over a small sample/)).toBeInTheDocument();
    expect(screen.getByText(/not a significance test/)).toBeInTheDocument();

    rerender(<CorrelationNote correlation={{ r: null, n: 1, minimum_pairs: 4 }} />);
    expect(screen.getByText(/within-subject correlation over a small sample/)).toBeInTheDocument();
  });
});

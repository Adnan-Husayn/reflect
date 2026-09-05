import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DistressIndicator } from "./DistressIndicator";
import { makeWellbeing } from "../test/factories";

/** Anything that would name a condition or make a claim about the person. */
const DIAGNOSTIC_PHRASES = [
  "diagnos",
  "depress",
  "disorder",
  "illness",
  "symptom",
  "you are",
  "at risk",
  "severe",
  "moderate",
  "mild",
];

/**
 * Everything the component asserts, minus its own disclaimer.
 *
 * The caveat necessarily contains "diagnose" — it is the sentence saying the
 * app does not — so scanning it would flag the very text that prevents the
 * problem. It is asserted separately below.
 */
function claimsIn(container: HTMLElement) {
  const clone = container.cloneNode(true) as HTMLElement;
  clone.querySelector(".distress-caveat")?.remove();
  return (clone.textContent ?? "").toLowerCase();
}

describe("DistressIndicator", () => {
  it.each(["insufficient_data", "steady", "observations"] as const)(
    "contains no diagnostic phrasing in the %s state",
    (status) => {
      const { container } = render(
        <DistressIndicator
          wellbeing={makeWellbeing({
            status,
            sustainedLowValence: status === "observations",
            sustainedConflict: status === "observations",
            lowValenceDays: 4,
            conflictDays: 4,
          })}
        />,
      );
      const text = claimsIn(container);
      for (const phrase of DIAGNOSTIC_PHRASES) {
        expect(text).not.toContain(phrase);
      }
    },
  );

  it.each(["insufficient_data", "steady", "observations"] as const)(
    "shows the components behind the headline in the %s state",
    (status) => {
      render(<DistressIndicator wellbeing={makeWellbeing({ status })} />);
      // The composite is never rendered alone.
      expect(screen.getByText("Days with enough data")).toBeInTheDocument();
      expect(screen.getByText("Low-valence days")).toBeInTheDocument();
      expect(screen.getByText("Conflict days")).toBeInTheDocument();
    },
  );

  it("distinguishes not-enough-data from a settled week", () => {
    const { rerender } = render(
      <DistressIndicator wellbeing={makeWellbeing({ status: "insufficient_data", daysWithData: 1 })} />,
    );
    expect(screen.getByText("Not enough recorded days yet")).toBeInTheDocument();
    // Explicitly not a reassurance nobody measured.
    expect(screen.getByText(/This is not a low result/)).toBeInTheDocument();

    rerender(<DistressIndicator wellbeing={makeWellbeing({ status: "steady" })} />);
    expect(screen.getByText("Nothing stood out this week")).toBeInTheDocument();
    expect(screen.queryByText(/not a low result/)).not.toBeInTheDocument();
  });

  it("describes observations rather than a state", () => {
    render(
      <DistressIndicator
        wellbeing={makeWellbeing({
          status: "observations",
          sustainedLowValence: true,
          lowValenceDays: 4,
        })}
      />,
    );
    expect(screen.getByText(/More low-valence readings than usual on/)).toBeInTheDocument();
  });

  it("reports each observation only when it was actually raised", () => {
    render(
      <DistressIndicator
        wellbeing={makeWellbeing({
          status: "observations",
          sustainedConflict: true,
          conflictDays: 3,
        })}
      />,
    );
    expect(screen.getByText(/Your channels disagreed with each other on/)).toBeInTheDocument();
    expect(screen.queryByText(/More low-valence readings/)).not.toBeInTheDocument();
  });

  it("states the rule and that a single day never counts", () => {
    render(<DistressIndicator wellbeing={makeWellbeing()} />);
    const caption = screen.getByText(/A day counts as low-valence when/);
    expect(caption).toHaveTextContent("3 or more of the last 7 days");
    expect(caption).toHaveTextContent("a single day never counts");
    expect(caption).toHaveTextContent("provisional");
  });

  it("says outright that it does not diagnose", () => {
    render(<DistressIndicator wellbeing={makeWellbeing()} />);
    expect(screen.getByText(/observations about recordings, not statements about you/)).toBeInTheDocument();
  });
});

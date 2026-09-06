import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DivergenceField } from "./DivergenceField";

describe("DivergenceField", () => {
  it("draws one line per channel", () => {
    const { container } = render(<DivergenceField />);
    expect(container.querySelectorAll(".field path")).toHaveLength(3);
  });

  it("names the three channels so the colours are not the only cue", () => {
    render(<DivergenceField />);
    expect(screen.getByText("Spoken words")).toBeInTheDocument();
    expect(screen.getByText("Vocal expression")).toBeInTheDocument();
    expect(screen.getByText("Visible facial expression")).toBeInTheDocument();
  });

  it("describes itself for anyone not using a cursor", () => {
    render(<DivergenceField />);
    const figure = screen.getByRole("img");
    expect(figure).toHaveAccessibleName(/following the cursor with different strengths/);
  });

  it("shows a divergence reading against the provisional threshold", () => {
    render(<DivergenceField />);
    expect(screen.getByText("provisional threshold 0.35")).toBeInTheDocument();
    expect(screen.getByText(/^0\.\d\d$/)).toBeInTheDocument();
  });

  it("reads as agreement while the channels sit together at rest", () => {
    render(<DivergenceField />);
    expect(screen.getByText("the channels agree")).toBeInTheDocument();
  });

  it("explains what the interaction demonstrates", () => {
    render(<DivergenceField />);
    expect(screen.getByText(/Each channel follows it with a different pull/)).toBeInTheDocument();
  });
});

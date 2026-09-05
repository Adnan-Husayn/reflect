import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SelfCarePrompts } from "./SelfCarePrompts";

const prompt = {
  key: "sustained_low_valence",
  observation: "More of your readings than usual have been low-valence this week.",
  suggestion: "If that matches how the week felt, it can help to tell one person you trust.",
};

describe("SelfCarePrompts", () => {
  it("renders exactly what the server supplied", () => {
    render(<SelfCarePrompts prompts={[prompt]} />);
    expect(screen.getByText(prompt.observation)).toBeInTheDocument();
    expect(screen.getByText(prompt.suggestion)).toBeInTheDocument();
  });

  it("renders nothing when no observation was raised", () => {
    const { container } = render(<SelfCarePrompts prompts={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says the suggestions are fixed rather than written for the reader", () => {
    render(<SelfCarePrompts prompts={[prompt]} />);
    expect(screen.getByText(/not advice about your health/)).toBeInTheDocument();
    expect(
      screen.getByText(/nothing here is written in response to your particular answers/),
    ).toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TypedTextFallback } from "./TypedTextFallback";
import { makePrediction } from "../test/factories";

describe("TypedTextFallback", () => {
  it("keeps the analyse button disabled until there is non-blank text", async () => {
    const user = userEvent.setup();
    render(<TypedTextFallback onAnalyze={vi.fn()} />);

    const button = screen.getByRole("button", { name: "Analyze text" });
    expect(button).toBeDisabled();

    await user.type(screen.getByLabelText("Text to analyze"), "   ");
    expect(button).toBeDisabled();

    await user.type(screen.getByLabelText("Text to analyze"), "hello");
    expect(button).toBeEnabled();
  });

  it("trims the text before sending it and renders the result", async () => {
    const user = userEvent.setup();
    const onAnalyze = vi.fn().mockResolvedValue(makePrediction({ joy: 0.9, neutral: 0.1 }));
    render(<TypedTextFallback onAnalyze={onAnalyze} />);

    await user.type(screen.getByLabelText("Text to analyze"), "  I feel good  ");
    await user.click(screen.getByRole("button", { name: "Analyze text" }));

    expect(onAnalyze).toHaveBeenCalledWith("I feel good");
    await waitFor(() => expect(screen.getByText("Model confidence 90%")).toBeInTheDocument());
  });

  it("shows the failure reason and stays usable", async () => {
    const user = userEvent.setup();
    const onAnalyze = vi.fn().mockRejectedValue(new Error("Text emotion model is currently unavailable."));
    render(<TypedTextFallback onAnalyze={onAnalyze} />);

    await user.type(screen.getByLabelText("Text to analyze"), "hello");
    await user.click(screen.getByRole("button", { name: "Analyze text" }));

    await waitFor(() =>
      expect(screen.getByText("Text emotion model is currently unavailable.")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Analyze text" })).toBeEnabled();
  });

  it("caps typed input at the backend's 5000-character limit", async () => {
    render(<TypedTextFallback onAnalyze={vi.fn()} />);
    const textarea = screen.getByLabelText("Text to analyze") as HTMLTextAreaElement;
    expect(textarea.maxLength).toBe(5000);
  });
});

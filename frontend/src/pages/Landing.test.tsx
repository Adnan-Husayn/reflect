import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Landing } from "./Landing";
import type { AuthState } from "../hooks/useAuth";

function renderPage(account: AuthState = null) {
  return render(
    <MemoryRouter>
      <Landing account={account} />
    </MemoryRouter>,
  );
}

describe("Landing", () => {
  it("is reachable without an account and does not ask for one first", () => {
    renderPage(null);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Three readings.");
    // The whole point: a visitor sees the product, not a sign-in form.
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("offers registration and sign-in to a signed-out visitor", () => {
    renderPage(null);
    expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute(
      "href",
      "/register",
    );
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("sends a signed-in visitor straight to their session", () => {
    renderPage({ id: "u-1", email: "tester@example.com" });
    expect(screen.getByRole("link", { name: "Go to your session" })).toHaveAttribute(
      "href",
      "/session",
    );
    expect(screen.queryByRole("link", { name: "Create an account" })).not.toBeInTheDocument();
  });

  // ── the copy must describe the app that shipped ──────────────────

  it("does not repeat the v0.3 claim that channels are never combined", () => {
    const { container } = renderPage();
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("never averaged");
    expect(text).not.toContain("no combined score");
    // Fusion shipped, so the honest claim is about the components staying visible.
    expect(screen.getByText("No score without its components")).toBeInTheDocument();
  });

  it("does not repeat the v0.3 claim that there are no accounts or history", () => {
    const { container } = renderPage();
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("no accounts");
    expect(text).not.toContain("no database and no authentication");
  });

  it("states what is actually stored and that deletion is real", () => {
    renderPage();
    expect(screen.getByText("No recordings kept")).toBeInTheDocument();
    expect(screen.getByText(/Only derived score vectors are stored/)).toBeInTheDocument();
    expect(screen.getByText(/deleting your data removes them outright/)).toBeInTheDocument();
  });

  it("keeps the conflict caveat that the rest of the app carries", () => {
    renderPage();
    const caveat = screen.getByText(/A conflict means the channels disagree/);
    expect(caveat).toHaveTextContent("not");
    expect(caveat).toHaveTextContent("concealing an emotion");
    expect(caveat).toHaveTextContent("not a diagnosis");
  });

  it("says the threshold is provisional rather than implying it was measured", () => {
    renderPage();
    expect(screen.getByText(/has not yet been derived from held-out labelled data/)).toBeInTheDocument();
  });

  it("credits the checkpoints as external work", () => {
    renderPage();
    expect(screen.getByText("The models are not ours.")).toBeInTheDocument();
    expect(screen.getByText("j-hartmann/emotion-english-distilroberta-base")).toBeInTheDocument();
    expect(screen.getByText("faster-whisper base.en")).toBeInTheDocument();
  });

  it("invents no social proof", () => {
    const { container } = renderPage();
    const text = (container.textContent ?? "").toLowerCase();
    // Word boundaries, not substrings: "rated" is inside "generated".
    const claims = [
      /\btrusted by\b/,
      /\busers love\b/,
      /\btestimonial/,
      /\bjoin thousands\b/,
      /\b\d+[,\d]* (users|people|students)\b/,
      /\brated \d/,
    ];
    for (const claim of claims) {
      expect(text).not.toMatch(claim);
    }
  });
});

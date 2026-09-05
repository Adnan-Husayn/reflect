import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionDetail } from "./SessionDetail";
import { makeScores } from "../test/factories";
import * as api from "../services/api";

const detail = {
  id: "s-1",
  started_at: "2026-09-01T10:00:00Z",
  ended_at: "2026-09-01T10:12:00Z",
  summary: {
    session_id: "s-1",
    n_readings: 120,
    n_fused_readings: 80,
    mean_valence: -0.25,
    conflict_rate: 0.4,
    dominant_label: "sadness" as const,
    channel_counts: { face: 60, voice: 30, text: 30 },
    computed_at: "2026-09-01T10:12:00Z",
  },
  readings: [
    {
      t: "2026-09-01T10:00:05Z",
      channel: "face" as const,
      label: "sadness" as const,
      confidence: 0.7,
      scores: makeScores({ sadness: 1 }),
    },
  ],
  fused_readings: [],
};

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${id}`]}>
      <Routes>
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionDetail", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders a session that exists", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(detail);
    renderAt("s-1");

    expect(await screen.findByText("80")).toBeInTheDocument();
    expect(screen.getByText("-0.25")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("sadness")).toBeInTheDocument();
  });

  it("reads the id from the URL so the page is shareable", async () => {
    const getSession = vi.spyOn(api, "getSession").mockResolvedValue(detail);
    renderAt("s-1");
    await screen.findByText("80");
    expect(getSession).toHaveBeenCalledWith("s-1");
  });

  it("shows a not-found state for a session that does not exist", async () => {
    vi.spyOn(api, "getSession").mockRejectedValue(new Error("Session not found."));
    renderAt("missing");
    expect(await screen.findByText("Session not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to trends" })).toBeInTheDocument();
  });

  it("says transcripts are not stored", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(detail);
    renderAt("s-1");
    expect(await screen.findByText(/Transcripts\s+are not stored/)).toBeInTheDocument();
  });

  it("explains a session that has no rollup", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue({ ...detail, summary: null, ended_at: null });
    renderAt("s-1");
    expect(await screen.findByText("No summary")).toBeInTheDocument();
    expect(screen.getByText(/it was never ended/)).toBeInTheDocument();
  });
});

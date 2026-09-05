import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Trends } from "./Trends";
import { makeBucket, makeTrends } from "../test/factories";
import * as api from "../services/api";

const trends = makeTrends([
  makeBucket({ date: "2026-09-01", readings: 80, valence: 0.5 }),
  makeBucket({ date: "2026-09-02", readings: 3 }),
]);

const session = {
  id: "s-1",
  started_at: "2026-09-01T10:00:00Z",
  ended_at: "2026-09-01T10:12:00Z",
  summary: {
    session_id: "s-1",
    n_readings: 120,
    n_fused_readings: 80,
    mean_valence: 0.5,
    conflict_rate: 0.2,
    dominant_label: "joy" as const,
    channel_counts: { face: 60, voice: 30, text: 30 },
    computed_at: "2026-09-01T10:12:00Z",
  },
};

function renderPage() {
  return render(
    <MemoryRouter>
      <Trends />
    </MemoryRouter>,
  );
}

describe("Trends", () => {
  beforeEach(() => {
    vi.spyOn(api, "getTrends").mockResolvedValue(trends);
    vi.spyOn(api, "getSessions").mockResolvedValue([session]);
  });

  afterEach(() => vi.restoreAllMocks());

  it("renders every chart with its caption", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Mood valence" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "PHQ-8 check-in score" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cross-channel conflict" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Channel coverage" })).toBeInTheDocument();
    expect(screen.getByText(/Weighted mean over fused readings/)).toBeInTheDocument();
  });

  it("shows the correlation with its sample size", async () => {
    vi.spyOn(api, "getTrends").mockResolvedValue(
      makeTrends(trends.buckets, { r: -0.58, n: 9, minimum_pairs: 4 }),
    );
    renderPage();

    expect(await screen.findByText("r = -0.58")).toBeInTheDocument();
    expect(screen.getByText("over n = 9 paired days")).toBeInTheDocument();
  });

  it("withholds the correlation until there are enough pairs", async () => {
    renderPage();
    expect(await screen.findByText(/0 of the 4 needed/)).toBeInTheDocument();
    expect(screen.queryByText(/^r = /)).not.toBeInTheDocument();
  });

  it("lists recorded sessions as links", async () => {
    renderPage();
    const link = await screen.findByRole("link", { name: /2026/ });
    expect(link).toHaveAttribute("href", "/sessions/s-1");
    expect(screen.getByText(/80 fused readings/)).toBeInTheDocument();
  });

  it("explains what to do when nothing has been recorded", async () => {
    vi.spyOn(api, "getSessions").mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No recorded sessions yet")).toBeInTheDocument();
    expect(screen.getByText(/Start a session on the/)).toBeInTheDocument();
    // An empty axis explains nothing, so no chart is drawn at all.
    expect(screen.queryByRole("heading", { name: "Mood valence" })).not.toBeInTheDocument();
  });

  it("treats a session that was never ended as unrecorded", async () => {
    vi.spyOn(api, "getSessions").mockResolvedValue([
      { id: "open", started_at: "2026-09-02T10:00:00Z", ended_at: null, summary: null },
    ]);
    renderPage();
    expect(await screen.findByText("No recorded sessions yet")).toBeInTheDocument();
  });

  it("refetches when the range changes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("heading", { name: "Mood valence" });

    await user.click(screen.getByRole("button", { name: "7 days" }));

    await waitFor(() => expect(api.getTrends).toHaveBeenCalledWith(7));
  });

  it("surfaces a load failure instead of an empty page", async () => {
    vi.spyOn(api, "getTrends").mockRejectedValue(new Error("Trends are unavailable."));
    renderPage();
    expect(await screen.findByText("Trends are unavailable.")).toBeInTheDocument();
  });
});

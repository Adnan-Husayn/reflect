import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CheckIn } from "./CheckIn";
import { makeInstrument } from "../test/factories";
import * as api from "../services/api";

const instrument = makeInstrument();

/** Anything that would read as a clinical interpretation of a total. */
const SEVERITY_WORDS = [
  "mild",
  "moderate",
  "moderately severe",
  "severe",
  "minimal",
  "cutoff",
  "cut-off",
  "depressed range",
  "at risk",
];

function checkin(score: number, takenOn = "2026-09-06") {
  return {
    id: `c-${takenOn}`,
    taken_on: takenOn,
    instrument: "PHQ-8",
    responses: {},
    score,
  };
}

async function answerAll(user: ReturnType<typeof userEvent.setup>, value = "Not at all") {
  const groups = screen.getAllByRole("group");
  for (const group of groups) {
    await user.click(within(group).getByRole("radio", { name: value }));
  }
}

describe("CheckIn", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(api, "getInstrument").mockResolvedValue(instrument);
    vi.spyOn(api, "getCheckins").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  // ── consent ─────────────────────────────────────────────────────

  it("gates the first check-in behind consent", async () => {
    render(<CheckIn />);
    expect(await screen.findByText("Before your first check-in")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit check-in" })).not.toBeInTheDocument();
  });

  it("says item-level answers are stored, not only the total", async () => {
    render(<CheckIn />);
    expect(
      await screen.findByText(/Answers are stored individually, not only as a score/),
    ).toBeInTheDocument();
  });

  it("does not show the gate again once accepted", async () => {
    const user = userEvent.setup();
    render(<CheckIn />);
    await user.click(await screen.findByRole("button", { name: /I understand/ }));

    expect(screen.queryByText("Before your first check-in")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Submit check-in" })).toBeInTheDocument();
  });

  // ── the form ────────────────────────────────────────────────────

  it("cannot be submitted with unanswered items", async () => {
    const user = userEvent.setup();
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    const submit = await screen.findByRole("button", { name: "Submit check-in" });
    expect(submit).toBeDisabled();

    const groups = screen.getAllByRole("group");
    await user.click(within(groups[0]).getByRole("radio", { name: "Not at all" }));
    expect(submit).toBeDisabled();

    await answerAll(user);
    expect(submit).toBeEnabled();
  });

  it("submits every answer with a total matching their sum", async () => {
    const user = userEvent.setup();
    const postCheckin = vi.spyOn(api, "postCheckin").mockResolvedValue(checkin(8));
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    await screen.findByRole("button", { name: "Submit check-in" });
    await answerAll(user, "Several days");
    await user.click(screen.getByRole("button", { name: "Submit check-in" }));

    await waitFor(() => expect(postCheckin).toHaveBeenCalled());
    const sent = postCheckin.mock.calls[0][0];
    expect(Object.keys(sent.responses)).toHaveLength(8);
    expect(sent.score).toBe(8);
    expect(sent.score).toBe(Object.values(sent.responses).reduce((a, b) => a + b, 0));
  });

  it("surfaces a same-day rejection as a readable message", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "postCheckin").mockRejectedValue(
      new Error("A PHQ-8 check-in already exists for 2026-09-06."),
    );
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    await screen.findByRole("button", { name: "Submit check-in" });
    await answerAll(user);
    await user.click(screen.getByRole("button", { name: "Submit check-in" }));

    expect(
      await screen.findByText("A PHQ-8 check-in already exists for 2026-09-06."),
    ).toBeInTheDocument();
  });

  // ── no interpretation ───────────────────────────────────────────

  it.each([0, 24])("renders no severity band at a score of %i", async (score) => {
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(score)]);
    localStorage.setItem("reflect.checkin.consent", "true");
    const { container } = render(<CheckIn />);

    await screen.findByRole("heading", { name: "Your check-ins" });
    const text = container.textContent?.toLowerCase() ?? "";
    for (const word of SEVERITY_WORDS) {
      expect(text).not.toContain(word);
    }
  });

  it.each([0, 24])("shows helpline details at a score of %i", async (score) => {
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(score)]);
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    expect(await screen.findByText("14416")).toBeInTheDocument();
    expect(screen.getByText("1800 599 0019")).toBeInTheDocument();
  });

  it("shows helplines before consent too", async () => {
    render(<CheckIn />);
    expect(await screen.findByText("14416")).toBeInTheDocument();
  });

  // ── cadence ─────────────────────────────────────────────────────

  it("says when the next check-in is due", async () => {
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(6, "2026-09-01")]);
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    expect(await screen.findByText(/Next one due/)).toBeInTheDocument();
    expect(screen.getByText(/weekly is enough/)).toBeInTheDocument();
  });
});

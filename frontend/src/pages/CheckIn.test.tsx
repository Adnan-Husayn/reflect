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

/** The item fieldsets only — the instrument picker is also a role="group". */
function itemGroups() {
  return screen
    .getAllByRole("group")
    .filter((group) => group.getAttribute("aria-label") !== "Questionnaire");
}

async function answerAll(user: ReturnType<typeof userEvent.setup>, value = "Not at all") {
  for (const group of itemGroups()) {
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

    await user.click(within(itemGroups()[0]).getByRole("radio", { name: "Not at all" }));
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

  // ── the audit additions ─────────────────────────────────────────

  it("offers both instruments and reloads the questionnaire on switch", async () => {
    const user = userEvent.setup();
    const getInstrument = vi.spyOn(api, "getInstrument").mockResolvedValue(instrument);
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    await screen.findByRole("button", { name: "Submit check-in" });
    expect(getInstrument).toHaveBeenCalledWith("PHQ-8");

    await user.click(screen.getByRole("button", { name: "GAD-7" }));
    await waitFor(() => expect(getInstrument).toHaveBeenCalledWith("GAD-7"));
  });

  it("removes a single check-in without touching the rest", async () => {
    const user = userEvent.setup();
    const deleteCheckin = vi.spyOn(api, "deleteCheckin").mockResolvedValue(undefined);
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(6), checkin(9, "2026-08-30")]);
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    await screen.findByRole("heading", { name: "Your check-ins" });
    const remove = screen.getAllByRole("button", { name: "Remove" });
    expect(remove).toHaveLength(2);

    await user.click(remove[0]);

    await waitFor(() => expect(deleteCheckin).toHaveBeenCalledWith("c-2026-09-06"));
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1),
    );
  });

  it("offers the data as CSV rather than only on screen", async () => {
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(6)]);
    localStorage.setItem("reflect.checkin.consent", "true");
    render(<CheckIn />);

    expect(await screen.findByRole("link", { name: "check-ins as CSV" })).toHaveAttribute(
      "href",
      expect.stringContaining("/export/checkins.csv"),
    );
    expect(screen.getByRole("link", { name: "sessions as CSV" })).toHaveAttribute(
      "href",
      expect.stringContaining("/export/sessions.csv"),
    );
  });

  it("labels which instrument each past entry was", async () => {
    vi.spyOn(api, "getCheckins").mockResolvedValue([checkin(6)]);
    localStorage.setItem("reflect.checkin.consent", "true");
    const { container } = render(<CheckIn />);

    await screen.findByRole("heading", { name: "Your check-ins" });
    // "PHQ-8" is also the picker's button label, so scope to the history.
    const history = container.querySelector(".checkin-history") as HTMLElement;
    expect(within(history).getByText("PHQ-8")).toBeInTheDocument();
  });
});

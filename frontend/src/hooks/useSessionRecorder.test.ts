import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionRecorder } from "./useSessionRecorder";
import { makeScores } from "../test/factories";

const FLUSH_MS = 15_000;

function reading(channel: "text" | "voice" | "face" = "face") {
  return {
    t: "2026-09-05T12:00:00.000Z",
    channel,
    label: "joy" as const,
    confidence: 0.8,
    scores: makeScores({ joy: 1 }),
  };
}

function fusedReading() {
  return {
    t: "2026-09-05T12:00:00.000Z",
    label: "joy" as const,
    confidence: 0.4,
    raw_confidence: 0.8,
    attenuation: 0.5,
    max_divergence: 0.5,
    conflict: true,
    scores: makeScores({ joy: 1 }),
  };
}

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    createSession: vi.fn().mockResolvedValue({ id: "s-1", started_at: "", ended_at: null }),
    postReadings: vi.fn().mockResolvedValue({}),
    endSession: vi.fn().mockResolvedValue({}),
    ...overrides,
  };
}

describe("useSessionRecorder", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("opens a session and reports that it is recording", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));

    await act(async () => await result.current.start());

    expect(api.createSession).toHaveBeenCalledOnce();
    expect(result.current.isRecording).toBe(true);
  });

  it("buffers readings instead of sending one request each", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());

    act(() => {
      result.current.addReading(reading("face"));
      result.current.addReading(reading("voice"));
      result.current.addFusedReading(fusedReading());
    });

    expect(api.postReadings).not.toHaveBeenCalled();
    expect(result.current.pending()).toEqual({ readings: 2, fused: 1 });
  });

  it("flushes the buffer on the timer", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addReading(reading()));

    await act(async () => {
      vi.advanceTimersByTime(FLUSH_MS);
    });

    expect(api.postReadings).toHaveBeenCalledOnce();
    expect(api.postReadings.mock.calls[0][1].readings).toHaveLength(1);
    expect(result.current.pending()).toEqual({ readings: 0, fused: 0 });
  });

  it("flushes and closes the session on end", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addFusedReading(fusedReading()));

    await act(async () => await result.current.stop());

    expect(api.postReadings).toHaveBeenCalledOnce();
    expect(api.endSession).toHaveBeenCalledWith("s-1");
    expect(result.current.isRecording).toBe(false);
  });

  it("does not flush an empty buffer", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());

    await act(async () => {
      vi.advanceTimersByTime(FLUSH_MS * 2);
    });

    expect(api.postReadings).not.toHaveBeenCalled();
  });

  // ── failure modes ───────────────────────────────────────────────────

  it("keeps the session usable when it cannot be opened", async () => {
    const api = makeApi({ createSession: vi.fn().mockRejectedValue(new Error("db down")) });
    const { result } = renderHook(() => useSessionRecorder({ api }));

    await act(async () => await result.current.start());

    expect(result.current.isRecording).toBe(false);
    // Readings are simply discarded; nothing throws into the live session.
    act(() => result.current.addReading(reading()));
    expect(result.current.pending()).toEqual({ readings: 0, fused: 0 });
  });

  it("stops recording but does not throw when a flush fails", async () => {
    const api = makeApi({ postReadings: vi.fn().mockRejectedValue(new Error("gone")) });
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addReading(reading()));

    await act(async () => {
      vi.advanceTimersByTime(FLUSH_MS);
    });

    expect(result.current.isRecording).toBe(false);
  });

  it("drops a failed batch rather than retrying it forever", async () => {
    const api = makeApi({ postReadings: vi.fn().mockRejectedValue(new Error("gone")) });
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addReading(reading()));

    await act(async () => {
      vi.advanceTimersByTime(FLUSH_MS * 4);
    });

    // One attempt, not one per tick: an ever-growing retry queue in a long
    // session is a worse failure than a gap in the data.
    expect(api.postReadings).toHaveBeenCalledOnce();
    expect(result.current.pending()).toEqual({ readings: 0, fused: 0 });
  });

  it("ending an unrecorded session does not call the API", async () => {
    const api = makeApi({ createSession: vi.fn().mockRejectedValue(new Error("db down")) });
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());

    await act(async () => await result.current.stop());

    expect(api.postReadings).not.toHaveBeenCalled();
    expect(api.endSession).not.toHaveBeenCalled();
  });

  it("survives endSession failing", async () => {
    const api = makeApi({ endSession: vi.fn().mockRejectedValue(new Error("gone")) });
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());

    await act(async () => await result.current.stop());

    expect(result.current.isRecording).toBe(false);
  });

  it("discards readings left over from a previous session", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addReading(reading()));
    await act(async () => await result.current.stop());

    // A late response from the previous session must not join the next one.
    act(() => result.current.addReading(reading()));
    expect(result.current.pending()).toEqual({ readings: 0, fused: 0 });

    await act(async () => await result.current.start());
    expect(result.current.pending()).toEqual({ readings: 0, fused: 0 });
  });

  it("stops the flush timer when the session ends", async () => {
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    await act(async () => await result.current.stop());
    api.postReadings.mockClear();

    await act(async () => {
      vi.advanceTimersByTime(FLUSH_MS * 3);
    });

    expect(api.postReadings).not.toHaveBeenCalled();
  });

  // ── the audit regression ────────────────────────────────────────────

  it("stopping twice does not close the session twice", async () => {
    /* stop() now runs from the unmount cleanup as well as the button, so a
       user who clicks End session and then navigates away calls it twice. */
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => result.current.addReading(reading()));

    await act(async () => await result.current.stop());
    await act(async () => await result.current.stop());

    expect(api.endSession).toHaveBeenCalledOnce();
    expect(api.postReadings).toHaveBeenCalledOnce();
  });

  it("flushes what it is holding when the session is stopped abruptly", async () => {
    /* Leaving the page mid-session used to lose the buffer entirely, because
       stop() was reachable only from the End session button. */
    const api = makeApi();
    const { result } = renderHook(() => useSessionRecorder({ api }));
    await act(async () => await result.current.start());
    act(() => {
      result.current.addReading(reading("face"));
      result.current.addFusedReading(fusedReading());
    });

    await act(async () => await result.current.stop());

    const batch = api.postReadings.mock.calls[0][1];
    expect(batch.readings).toHaveLength(1);
    expect(batch.fused).toHaveLength(1);
    expect(api.endSession).toHaveBeenCalledWith("s-1");
  });
});

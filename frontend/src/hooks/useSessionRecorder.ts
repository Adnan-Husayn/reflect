import { useCallback, useRef, useState } from "react";
import { createSession, endSession, postReadings } from "../services/api";
import type { FusedReadingIn, ReadingIn } from "../types/emotion";

export const FLUSH_INTERVAL_MS = 15_000;

interface SessionRecorderApi {
  createSession: typeof createSession;
  postReadings: typeof postReadings;
  endSession: typeof endSession;
}

interface Options {
  /** Injected in tests; defaults to the real client. */
  api?: Partial<SessionRecorderApi>;
  flushIntervalMs?: number;
}

/**
 * Buffers derived readings and flushes them to the session API.
 *
 * Recording never blocks the live session. If the session cannot be opened, or
 * a flush fails, the indicators keep working and the session simply is not
 * recorded — the app exists to show live indicators, and storage serves M4.
 *
 * Failed flushes drop their buffer rather than retrying. An ever-growing retry
 * queue in a long session is a worse failure than a gap in the data.
 */
export function useSessionRecorder({ api, flushIntervalMs = FLUSH_INTERVAL_MS }: Options = {}) {
  const client: SessionRecorderApi = {
    createSession: api?.createSession ?? createSession,
    postReadings: api?.postReadings ?? postReadings,
    endSession: api?.endSession ?? endSession,
  };

  const sessionId = useRef<string | null>(null);
  const readings = useRef<ReadingIn[]>([]);
  const fused = useRef<FusedReadingIn[]>([]);
  const timer = useRef<number | null>(null);
  const flushing = useRef(false);
  const [isRecording, setIsRecording] = useState(false);

  const drain = useCallback(() => {
    const batch = { readings: readings.current, fused: fused.current };
    readings.current = [];
    fused.current = [];
    return batch;
  }, []);

  const flush = useCallback(async () => {
    const id = sessionId.current;
    if (!id || flushing.current) return;
    if (readings.current.length === 0 && fused.current.length === 0) return;

    // Drain before awaiting, so readings arriving mid-request are not lost.
    const batch = drain();
    flushing.current = true;
    try {
      await client.postReadings(id, batch);
    } catch {
      // Dropped on purpose. See the note on retry queues above.
      setIsRecording(false);
      sessionId.current = null;
    } finally {
      flushing.current = false;
    }
  }, [client, drain]);

  const start = useCallback(async () => {
    readings.current = [];
    fused.current = [];
    try {
      const session = await client.createSession();
      sessionId.current = session.id;
      setIsRecording(true);
      timer.current = window.setInterval(() => void flush(), flushIntervalMs);
    } catch {
      // The database being down must not take the demo down with it.
      sessionId.current = null;
      setIsRecording(false);
    }
  }, [client, flush, flushIntervalMs]);

  const stop = useCallback(async () => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
    const id = sessionId.current;
    if (!id) {
      readings.current = [];
      fused.current = [];
      return;
    }
    await flush();
    try {
      await client.endSession(id);
    } catch {
      // Nothing useful to tell the user: the readings are already written or
      // already lost, and the session row is closed by the next run either way.
    }
    sessionId.current = null;
    setIsRecording(false);
  }, [client, flush]);

  const addReading = useCallback((reading: ReadingIn) => {
    if (!sessionId.current) return;
    readings.current.push(reading);
  }, []);

  const addFusedReading = useCallback((reading: FusedReadingIn) => {
    if (!sessionId.current) return;
    fused.current.push(reading);
  }, []);

  return {
    isRecording,
    start,
    stop,
    addReading,
    addFusedReading,
    /** Test seam: what is waiting to be sent. */
    pending: () => ({ readings: readings.current.length, fused: fused.current.length }),
  };
}

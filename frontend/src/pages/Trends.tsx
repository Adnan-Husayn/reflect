import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChannelCoverage } from "../components/charts/ChannelCoverage";
import { CheckInTrend } from "../components/charts/CheckInTrend";
import { ConflictTrend } from "../components/charts/ConflictTrend";
import { CorrelationNote } from "../components/CorrelationNote";
import { ValenceTrend } from "../components/charts/ValenceTrend";
import { EmptyState } from "../components/EmptyState";
import { StatusMessage } from "../components/StatusMessage";
import { getSessions, getTrends } from "../services/api";
import type { SessionListItem, TrendsOut } from "../types/emotion";

const RANGES = [7, 30, 90];

const formatDate = (value: string) =>
  new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function Trends() {
  const [days, setDays] = useState(30);
  const [trends, setTrends] = useState<TrendsOut | null>(null);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async (range: number) => {
    setIsLoading(true);
    try {
      const [nextTrends, nextSessions] = await Promise.all([getTrends(range), getSessions()]);
      setTrends(nextTrends);
      setSessions(nextSessions);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Trends are unavailable.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(days);
  }, [days, load]);

  const recorded = sessions.filter((session) => session.summary !== null);

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>Trends</h1>
        <p>How the recorded sessions change over time. Every chart states what it is computed from.</p>
      </header>

      <StatusMessage message={error} />

      <div className="range-picker" role="group" aria-label="Date range">
        {RANGES.map((range) => (
          <button
            key={range}
            type="button"
            className={range === days ? "range-button active" : "range-button"}
            aria-pressed={range === days}
            onClick={() => setDays(range)}
          >
            {range} days
          </button>
        ))}
      </div>

      {isLoading && !trends ? (
        <p className="loading-note">Loading trends…</p>
      ) : recorded.length === 0 ? (
        <EmptyState title="No recorded sessions yet">
          Trends are drawn from completed sessions. Start a session on the{" "}
          <Link to="/">live session</Link> page, let it run for a minute or two, then end it —
          the charts appear here once there is something to draw.
        </EmptyState>
      ) : (
        trends && (
          <>
            <div className="chart-stack">
              <ValenceTrend trends={trends} />
              {/* Stacked below valence on the same date axis rather than
                  overlaid on a second y-axis — the two scales run in opposite
                  directions and sharing one chart would imply a relationship
                  the scaling chose. */}
              <CheckInTrend trends={trends} />
              <CorrelationNote correlation={trends.correlation} />
              <ConflictTrend trends={trends} />
              <ChannelCoverage trends={trends} />
            </div>

            <section className="session-list" aria-labelledby="sessions-heading">
              <h2 id="sessions-heading">Sessions</h2>
              <ul>
                {recorded.map((session) => (
                  <li key={session.id}>
                    <Link to={`/sessions/${session.id}`}>{formatDate(session.started_at)}</Link>
                    <span className="session-list-meta">
                      {session.summary?.n_fused_readings ?? 0} fused readings
                      {session.summary?.dominant_label ? ` · mostly ${session.summary.dominant_label}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )
      )}
    </main>
  );
}

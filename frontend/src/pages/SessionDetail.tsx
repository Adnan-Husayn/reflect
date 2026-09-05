import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { getSession } from "../services/api";
import type { SessionDetail as SessionDetailData } from "../types/emotion";

const formatDate = (value: string) =>
  new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<SessionDetailData | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    getSession(sessionId)
      .then((detail) => {
        if (!cancelled) setSession(detail);
      })
      .catch(() => {
        if (!cancelled) setNotFound(true);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (isLoading) {
    return (
      <main className="page-shell">
        <p className="loading-note">Loading session…</p>
      </main>
    );
  }

  if (notFound || !session) {
    return (
      <main className="page-shell">
        <EmptyState title="Session not found">
          This session may have been deleted. <Link to="/trends">Back to trends</Link>.
        </EmptyState>
      </main>
    );
  }

  const summary = session.summary;

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="project-code">
          <Link to="/trends">Trends</Link> / Session
        </p>
        <h1>{formatDate(session.started_at)}</h1>
        <p>
          {session.ended_at ? `Ended ${formatDate(session.ended_at)}.` : "Still open."} Transcripts
          are not stored, so this shows emotion trajectories but never the words spoken.
        </p>
      </header>

      {summary ? (
        <dl className="summary-grid">
          <div>
            <dt>Fused readings</dt>
            <dd>{summary.n_fused_readings}</dd>
          </div>
          <div>
            <dt>Channel readings</dt>
            <dd>{summary.n_readings}</dd>
          </div>
          <div>
            <dt>Mean valence</dt>
            <dd>{summary.mean_valence === null ? "—" : summary.mean_valence.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Conflict rate</dt>
            <dd>
              {summary.conflict_rate === null ? "—" : `${Math.round(summary.conflict_rate * 100)}%`}
            </dd>
          </div>
          <div>
            <dt>Most frequent</dt>
            <dd>{summary.dominant_label ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <EmptyState title="No summary">
          This session has no rollup, which means it was never ended.
        </EmptyState>
      )}

      <p className="detail-note">
        Mean valence is a weighted mean over this session's fused readings, where joy is +1, anger,
        disgust, fear and sadness are −1, and neutral and surprise are 0.
      </p>
    </main>
  );
}

import { useEffect, useState } from "react";
import { DistressIndicator } from "../components/DistressIndicator";
import { SelfCarePrompts } from "../components/SelfCarePrompts";
import { StatusMessage } from "../components/StatusMessage";
import { SupportInfo } from "../components/SupportInfo";
import { getWellbeing } from "../services/api";
import type { Wellbeing as WellbeingData } from "../types/emotion";

export function Wellbeing() {
  const [wellbeing, setWellbeing] = useState<WellbeingData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getWellbeing()
      .then((data) => {
        if (!cancelled) setWellbeing(data);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "This page is unavailable.");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="project-code">PCS26/146</p>
        <h1>This week</h1>
        <p>What the last week of recordings showed, and what it did not.</p>
      </header>

      <StatusMessage message={error} />

      {isLoading ? (
        <p className="loading-note">Loading…</p>
      ) : (
        wellbeing && (
          <>
            <DistressIndicator wellbeing={wellbeing} />
            <SelfCarePrompts prompts={wellbeing.prompts} />
          </>
        )
      )}

      {/* Rendered in every state, including the healthiest and the empty one.
          Support that appears only above a threshold would announce a verdict
          by its own arrival. */}
      <SupportInfo />
    </main>
  );
}

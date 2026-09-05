import type { TrendBucket } from "../../types/emotion";

export const axisDate = (value: string) =>
  new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });

interface TrendTooltipProps {
  active?: boolean;
  payload?: { payload: TrendBucket }[];
  valueKey: "mean_valence" | "conflict_rate";
  label: string;
  percent?: boolean;
}

/**
 * Shows the value alongside the counts it was computed from, so a reader can
 * see how much a point is worth before reading anything into it.
 */
export function TrendTooltip({ active, payload, valueKey, label, percent }: TrendTooltipProps) {
  if (!active || !payload?.length) return null;
  const bucket = payload[0].payload;
  const value = bucket[valueKey];

  return (
    <div className="chart-tooltip">
      <strong>{axisDate(bucket.date)}</strong>
      {value === null ? (
        <p className="chart-tooltip-gap">
          Not enough readings to report — shown as a gap.
        </p>
      ) : (
        <p>
          {label}: <strong>{percent ? `${Math.round(value * 100)}%` : value.toFixed(2)}</strong>
        </p>
      )}
      <p className="chart-tooltip-counts">
        {bucket.n_sessions} session{bucket.n_sessions === 1 ? "" : "s"} ·{" "}
        {bucket.n_fused_readings} fused reading{bucket.n_fused_readings === 1 ? "" : "s"}
      </p>
    </div>
  );
}

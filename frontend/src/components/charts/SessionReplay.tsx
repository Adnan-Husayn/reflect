import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartFrame } from "./ChartFrame";
import type { FusedReadingOut } from "../../types/emotion";
import { valenceOf } from "../../utils/valence";

const clockTime = (value: string) =>
  new Date(value).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

/**
 * The trajectory of one session.
 *
 * The endpoint already returned every reading and the page drew none of them —
 * hundreds of rows fetched to render five summary numbers.
 */
export function SessionReplay({ fused }: { fused: FusedReadingOut[] }) {
  if (fused.length === 0) return null;

  const data = fused.map((reading) => ({
    t: reading.t,
    valence: valenceOf(reading.scores),
    confidence: reading.confidence,
    label: reading.label,
    conflict: reading.conflict,
  }));

  return (
    <ChartFrame
      title="How the session went"
      computedFrom="Each point is one combined reading, plotted at the time it was taken. Valence uses the same map as the trends page — joy is +1; anger, disgust, fear and sadness are −1; neutral and surprise are 0 — so this is the same quantity the daily mean is built from, before it was averaged. Transcripts are not stored, so this shows the trajectory but never the words."
    >
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#E6E0D1" vertical={false} />
          <XAxis dataKey="t" tickFormatter={clockTime} stroke="#9FA694" fontSize={11} tickLine={false} minTickGap={40} />
          <YAxis domain={[-1, 1]} ticks={[-1, 0, 1]} stroke="#9FA694" fontSize={11} tickLine={false} width={44} />
          <ReferenceLine y={0} stroke="#C9BCB1" />
          <Tooltip
            labelFormatter={clockTime}
            formatter={(value: number, name) =>
              name === "valence" ? [value.toFixed(2), "Valence"] : [value, name]
            }
          />
          <Line
            type="monotone"
            dataKey="valence"
            stroke="#545C4F"
            strokeWidth={1.5}
            dot={false}
            name="valence"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

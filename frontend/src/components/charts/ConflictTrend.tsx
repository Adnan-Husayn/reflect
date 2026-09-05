import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendsOut } from "../../types/emotion";
import { ChartFrame } from "./ChartFrame";
import { TrendTooltip, axisDate } from "./shared";

const percentTick = (value: number) => `${Math.round(value * 100)}%`;

export function ConflictTrend({ trends }: { trends: TrendsOut }) {
  return (
    <ChartFrame
      title="Cross-channel conflict"
      computedFrom={`The share of a day's fused readings whose channel divergence exceeded the provisional threshold, weighted by reading count. A conflict means the channels disagreed — it is not evidence of concealment. Days with fewer than ${trends.minimum_readings_per_day} fused readings are omitted.`}
    >
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={trends.buckets} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="date" tickFormatter={axisDate} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis domain={[0, 1]} ticks={[0, 0.5, 1]} tickFormatter={percentTick} stroke="#94a3b8" fontSize={11} tickLine={false} width={44} />
          <Tooltip content={<TrendTooltip valueKey="conflict_rate" label="Conflict rate" percent />} />
          <Bar dataKey="conflict_rate" fill="#9a4a2c" radius={[2, 2, 0, 0]} name="Conflict rate" />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

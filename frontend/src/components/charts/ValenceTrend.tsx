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
import type { TrendsOut } from "../../types/emotion";
import { ChartFrame } from "./ChartFrame";
import { TrendTooltip, axisDate } from "./shared";

export function ValenceTrend({ trends }: { trends: TrendsOut }) {
  return (
    <ChartFrame
      title="Mood valence"
      computedFrom={`Weighted mean over fused readings, using the valence map in utils/valence.py where joy is +1, anger, disgust, fear and sadness are −1, and neutral and surprise are 0. Days with fewer than ${trends.minimum_readings_per_day} fused readings are shown as gaps. The trend line is a ${trends.rolling_window_days}-day rolling mean weighted by reading count.`}
    >
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={trends.buckets} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="date" tickFormatter={axisDate} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis domain={[-1, 1]} ticks={[-1, -0.5, 0, 0.5, 1]} stroke="#94a3b8" fontSize={11} tickLine={false} width={44} />
          <ReferenceLine y={0} stroke="#cbd5e1" />
          <Tooltip content={<TrendTooltip valueKey="mean_valence" label="Valence" />} />
          {/* connectNulls stays false on purpose: a gap day must read as a
              gap, not be bridged into a continuous line. */}
          <Line type="monotone" dataKey="mean_valence" stroke="#475569" strokeWidth={1.5} dot={{ r: 2.5 }} connectNulls={false} name="Daily" />
          <Line type="monotone" dataKey="rolling_valence" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls={false} name="Rolling" />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

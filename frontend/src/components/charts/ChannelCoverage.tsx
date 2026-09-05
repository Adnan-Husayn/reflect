import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendsOut } from "../../types/emotion";
import { ChartFrame } from "./ChartFrame";
import { axisDate } from "./shared";

const CHANNELS = [
  { key: "text", name: "Spoken words", fill: "#4E6350" },
  { key: "voice", name: "Vocal expression", fill: "#6E6A42" },
  { key: "face", name: "Visible facial expression", fill: "#446B69" },
] as const;

export function ChannelCoverage({ trends }: { trends: TrendsOut }) {
  const data = trends.buckets.map((bucket) => ({
    date: bucket.date,
    text: bucket.channel_counts.text ?? 0,
    voice: bucket.channel_counts.voice ?? 0,
    face: bucket.channel_counts.face ?? 0,
  }));

  return (
    <ChartFrame
      title="Channel coverage"
      computedFrom="Reading counts per channel per day, not proportions. The question this answers is whether a channel was available at all — a denied camera shows as no facial readings. Counts differ between channels by design: facial frames are sampled every 2 seconds against the audio channel's 5."
    >
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="date" tickFormatter={axisDate} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} width={44} allowDecimals={false} />
          <Tooltip />
          <Legend iconType="square" wrapperStyle={{ fontSize: 11 }} />
          {CHANNELS.map((channel) => (
            <Bar key={channel.key} dataKey={channel.key} stackId="channels" fill={channel.fill} name={channel.name} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

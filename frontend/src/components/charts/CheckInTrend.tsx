import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendsOut } from "../../types/emotion";
import { ChartFrame } from "./ChartFrame";
import { axisDate } from "./shared";

const PHQ8_MAX = 24;

/**
 * Plotted on its own chart, below valence and sharing its date axis, rather
 * than overlaid on a second y-axis.
 *
 * PHQ-8 runs 0-24 where higher is worse; valence runs -1..+1 where higher is
 * better. Overlaying them would let arbitrary scaling imply a relationship,
 * and inverting an axis so both read "up is good" would hide the polarity flip
 * from anyone skimming.
 */
export function CheckInTrend({ trends }: { trends: TrendsOut }) {
  return (
    <ChartFrame
      title="PHQ-8 check-in score"
      computedFrom="The total of the eight PHQ-8 items, each scored 0 to 3, recomputed on the server from the individual answers. Runs 0 to 24, where a higher score means more symptoms reported — the opposite direction to valence above. Points appear only on days a check-in was submitted; the questionnaire is weekly. No score is graded or mapped onto a severity category."
    >
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={trends.buckets} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
          <CartesianGrid stroke="#E6E0D1" vertical={false} />
          <XAxis dataKey="date" tickFormatter={axisDate} stroke="#9FA694" fontSize={11} tickLine={false} />
          <YAxis domain={[0, PHQ8_MAX]} ticks={[0, 8, 16, 24]} stroke="#9FA694" fontSize={11} tickLine={false} width={44} />
          <Tooltip
            labelFormatter={axisDate}
            formatter={(value: number) => [`${value} of ${PHQ8_MAX}`, "PHQ-8"]}
          />
          {/* connectNulls joins the weekly points: the gaps between them are
              days with no questionnaire, not missing measurements. */}
          <Line
            type="monotone"
            dataKey="checkin_score"
            stroke="#545C4F"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
            name="PHQ-8"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

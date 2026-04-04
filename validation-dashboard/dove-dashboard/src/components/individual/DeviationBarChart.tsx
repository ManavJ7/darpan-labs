import {
  BarChart, Bar, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { deviationColor } from '../../lib/validation-utils';
import type { PerMetricEntry } from '../../types/individual';

interface Props {
  perMetric: PerMetricEntry[];
}

export function DeviationBarChart({ perMetric }: Props) {
  const data = perMetric.map((m) => ({
    metric: m.metric.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    diff: m.diff,
    color: deviationColor(m.diff),
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-[11px] font-medium text-text-secondary mb-2">
        Deviation (Twin - Real)
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ left: 80, right: 20, top: 5, bottom: 5 }}>
          <XAxis
            type="number"
            domain={[-4, 4]}
            tick={{ fill: '#666666', fontSize: 10 }}
            axisLine={{ stroke: '#2A2A2A' }}
            tickLine={{ stroke: '#2A2A2A' }}
          />
          <YAxis
            type="category"
            dataKey="metric"
            tick={{ fill: '#A0A0A0', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={75}
          />
          <ReferenceLine x={0} stroke="#2A2A2A" strokeWidth={2} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1A1A1A',
              border: '1px solid #2A2A2A',
              borderRadius: 8,
              fontSize: 12,
            }}
            itemStyle={{ color: '#FFFFFF' }}
            labelStyle={{ color: '#A0A0A0' }}
            formatter={(value) => [Number(value) > 0 ? `+${value}` : `${value}`, 'Deviation']}
          />
          <Bar dataKey="diff" radius={[0, 4, 4, 0]}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

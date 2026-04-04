import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { ConceptValidation } from '../../types/individual';

interface Props {
  concept: ConceptValidation;
}

export function RadarChartOverlay({ concept }: Props) {
  const allKeys = Array.from(
    new Set([...Object.keys(concept.real_metrics), ...Object.keys(concept.twin_metrics)])
  );

  const data = allKeys.map((key) => ({
    metric: (concept as any).per_metric?.find((m: any) => m.metric === key)
      ? key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
      : key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    real: concept.real_metrics[key] ?? 0,
    twin: concept.twin_metrics[key] ?? 0,
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-[11px] font-medium text-text-secondary mb-2">Real vs Twin Overlay</h3>
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="72%">
          <PolarGrid stroke="#2A2A2A" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: '#666666', fontSize: 10 }}
          />
          <PolarRadiusAxis
            domain={[0, 5]}
            tickCount={6}
            tick={{ fill: '#666666', fontSize: 9 }}
            axisLine={false}
          />
          <Radar
            name="Real"
            dataKey="real"
            stroke="#C8FF00"
            fill="#C8FF00"
            fillOpacity={0.15}
            strokeWidth={2}
          />
          <Radar
            name="Twin"
            dataKey="twin"
            stroke="#00D4FF"
            fill="#00D4FF"
            fillOpacity={0.15}
            strokeWidth={2}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            formatter={(value: string) => (
              <span style={{ color: value === 'Real' ? '#C8FF00' : '#00D4FF', fontSize: 11 }}>
                {value}
              </span>
            )}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1A1A1A',
              border: '1px solid #2A2A2A',
              borderRadius: 8,
              fontSize: 12,
            }}
            itemStyle={{ color: '#FFFFFF' }}
            labelStyle={{ color: '#A0A0A0' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

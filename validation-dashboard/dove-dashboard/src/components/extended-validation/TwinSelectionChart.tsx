import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { qualityColor } from '../../lib/validation-utils';
import type { TwinSelectionSummary } from '../../types/extended';

interface Props {
  summary: TwinSelectionSummary[];
}

export function TwinSelectionChart({ summary }: Props) {
  const data = summary.map((s) => ({
    twin: s.twin_id,
    count: s.times_selected,
    mae: s.avg_mae_when_selected,
    color: qualityColor(s.avg_mae_when_selected, 'mae'),
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Best-Match Twin Selection Frequency</h3>
        <span className="text-[10px] text-text-muted font-mono">
          Which twin variant was selected most often as best match
        </span>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <XAxis
              dataKey="twin"
              tick={{ fill: '#A0A0A0', fontSize: 11 }}
              axisLine={{ stroke: '#2A2A2A' }}
              tickLine={{ stroke: '#2A2A2A' }}
            />
            <YAxis
              tick={{ fill: '#666666', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
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
              formatter={(value) => [Number(value), 'Times Selected']}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry, idx) => (
                <Cell key={idx} fill={entry.color} fillOpacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-2 justify-center">
          {data.map((d) => (
            <div key={d.twin} className="flex items-center justify-between bg-surface rounded-lg px-3 py-2 border border-border">
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono text-white">{d.twin}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-mono text-text-secondary">
                  {d.count} / 17 selected
                </span>
                <span
                  className="text-[11px] font-mono px-2 py-0.5 rounded"
                  style={{ color: d.color, backgroundColor: `${d.color}15` }}
                >
                  MAE {d.mae?.toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

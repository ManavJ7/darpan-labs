import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { CONCEPT_COLORS } from '../../constants/theme';
import { useDashboardStore } from '../../store/useDashboardStore';
import type { DashboardData } from '../../types';

interface CompositeRankingChartProps {
  data: DashboardData;
}

export function CompositeRankingChart({ data }: CompositeRankingChartProps) {
  const dataSource = useDashboardStore((s) => s.dataSource);
  const focusedConcept = useDashboardStore((s) => s.focusedConcept);
  const setFocused = useDashboardStore((s) => s.setFocusedConcept);
  const drilldownMetric = useDashboardStore((s) => s.drilldownMetric);

  const conceptNames = data.metadata.concept_short_names;

  const chartData = conceptNames
    .map((name) => {
      let realVal: number | null = null;
      let twinVal: number | null = null;

      if (drilldownMetric) {
        realVal = data.real.t2b[name]?.[drilldownMetric]?.t2b ?? null;
        twinVal = data.twin.t2b[name]?.[drilldownMetric]?.t2b ?? null;
      } else {
        realVal = data.real.composites[name] ?? null;
        twinVal = data.twin.composites[name] ?? null;
      }

      return {
        name,
        real: realVal,
        twin: twinVal,
        tier: data.real.tiers[name],
        ranking: data.real.directRanking[name],
      };
    })
    .sort((a, b) => {
      const aVal = dataSource === 'twin' ? (a.twin ?? 0) : (a.real ?? 0);
      const bVal = dataSource === 'twin' ? (b.twin ?? 0) : (b.real ?? 0);
      return bVal - aVal;
    });

  const showBoth = dataSource === 'both';

  return (
    <div className="bg-card border border-border rounded-xl p-4" style={{ boxShadow: '0 0 20px rgba(200,255,0,0.03)' }}>
      {/* Legend for Real vs Twin */}
      {showBoth && (
        <div className="flex items-center gap-4 mb-3 pl-[100px]">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-white/70" />
            <span className="text-[10px] text-text-secondary font-mono">Real</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-white/25" />
            <span className="text-[10px] text-text-secondary font-mono">Twin</span>
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#666', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: '#2A2A2A' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={({ x, y, payload }) => {
              const d = chartData.find((c) => c.name === payload.value);
              const color = CONCEPT_COLORS[payload.value] || '#A0A0A0';
              const top3Pct = d?.ranking?.top3_pct ?? 0;
              const rankingLabel = top3Pct > 0 ? `Top-3: ${top3Pct}%` : 'Not in top-3';
              return (
                <g
                  onClick={() => setFocused(payload.value)}
                  className="cursor-pointer"
                >
                  <text
                    x={x}
                    y={y}
                    dy={-4}
                    textAnchor="end"
                    fill={color}
                    fontSize={12}
                    fontWeight={600}
                    opacity={!focusedConcept || focusedConcept === payload.value ? 1 : 0.3}
                  >
                    {payload.value}
                  </text>
                  <text
                    x={x}
                    y={y}
                    dy={10}
                    textAnchor="end"
                    fill="#666"
                    fontSize={9}
                    fontFamily="JetBrains Mono"
                    opacity={!focusedConcept || focusedConcept === payload.value ? 1 : 0.3}
                  >
                    {rankingLabel}
                  </text>
                </g>
              );
            }}
            axisLine={{ stroke: '#2A2A2A' }}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            contentStyle={{
              backgroundColor: '#111111',
              border: '1px solid #333',
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
              boxShadow: '0 0 15px rgba(200,255,0,0.1)',
              color: '#FFFFFF',
            }}
            labelStyle={{ color: '#A0A0A0' }}
            itemStyle={{ color: '#FFFFFF' }}
            formatter={(value, name) => [
              `${Number(value)?.toFixed(1)}%`,
              name === 'real' ? 'Real' : 'Twin',
            ]}
          />
          {(dataSource === 'real' || dataSource === 'both') && (
            <Bar dataKey="real" name="real" radius={[0, 4, 4, 0]} barSize={showBoth ? 14 : 22}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={CONCEPT_COLORS[entry.name]}
                  opacity={!focusedConcept || focusedConcept === entry.name ? 0.85 : 0.15}
                />
              ))}
            </Bar>
          )}
          {(dataSource === 'twin' || dataSource === 'both') && (
            <Bar dataKey="twin" name="twin" radius={[0, 4, 4, 0]} barSize={showBoth ? 14 : 22}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={CONCEPT_COLORS[entry.name]}
                  opacity={!focusedConcept || focusedConcept === entry.name
                    ? (showBoth ? 0.3 : 0.85)
                    : 0.08
                  }
                />
              ))}
            </Bar>
          )}
        </BarChart>
      </ResponsiveContainer>

      {/* Tier brackets */}
      <div className="flex gap-4 mt-2 px-4">
        {[1, 2].map((tier) => {
          const concepts = chartData.filter((d) => d.tier === tier);
          if (concepts.length === 0) return null;
          const tierColor = tier === 1 ? '#00FF88' : '#FF4444';
          return (
            <div
              key={tier}
              className="flex items-center gap-2 px-2 py-1 rounded text-[10px]"
              style={{
                backgroundColor: `${tierColor}10`,
                borderLeft: `2px solid ${tierColor}`,
              }}
            >
              <span className="font-mono font-semibold" style={{ color: tierColor }}>
                Tier {tier}
              </span>
              <span className="text-text-muted">
                {concepts.map((c) => c.name).join(', ')}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

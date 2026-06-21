import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import ChartCard from './ChartCard'
import { CATEGORICAL_COLORS, CHART_DEFAULTS } from './chartTheme'

export default function AreaChartCard({
  title, subtitle, action, emptyMessage,
  data = [], xKey = 'name', areas = [],
  stacked = false, height = 300, animate = true,
  colors = CATEGORICAL_COLORS, yFormatter,
}) {
  const empty = !data || data.length === 0

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div style={CHART_DEFAULTS.tooltip.contentStyle}>
        <p className="font-label-md font-bold text-on-surface mb-1">{label}</p>
        {payload.map((entry, i) => (
          <p key={i} className="text-body-md" style={{ color: entry.color }}>
            {entry.name}: {yFormatter ? yFormatter(entry.value) : typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    )
  }

  return (
    <ChartCard title={title} subtitle={subtitle} action={action} empty={empty} emptyMessage={emptyMessage}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <defs>
            {areas.map((area, i) => (
              <linearGradient key={area.key || i} id={`gradient_${area.key || i}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={area.color || colors[i % colors.length]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={area.color || colors[i % colors.length]} stopOpacity={0.05} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} tickFormatter={yFormatter} />
          <Tooltip content={<CustomTooltip />} />
          {areas.map((area, i) => (
            <Area
              key={area.key || i}
              type="monotone"
              dataKey={area.key || area.dataKey}
              name={area.name || area.key}
              stroke={area.color || colors[i % colors.length]}
              fill={`url(#gradient_${area.key || i})`}
              strokeWidth={2}
              stackId={stacked ? 'stack' : undefined}
              isAnimationActive={animate}
            />
          ))}
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

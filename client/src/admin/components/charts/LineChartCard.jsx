import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import ChartCard from './ChartCard'
import { CATEGORICAL_COLORS, CHART_DEFAULTS } from './chartTheme'

export default function LineChartCard({
  title, subtitle, action, emptyMessage,
  data = [], xKey = 'name', lines = [],
  height = 300, animate = true, referenceLines = [],
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
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} tickFormatter={yFormatter} />
          <Tooltip content={<CustomTooltip />} />
          {referenceLines.map((rl, i) => (
            <ReferenceLine key={i} y={rl.y} label={rl.label} stroke={rl.color || '#dc2626'} strokeDasharray="4 4" />
          ))}
          {lines.map((line, i) => (
            <Line
              key={line.key || i}
              type="monotone"
              dataKey={line.key || line.dataKey}
              name={line.name || line.key}
              stroke={line.color || colors[i % colors.length]}
              strokeWidth={2}
              dot={{ r: 3, fill: line.color || colors[i % colors.length], strokeWidth: 0 }}
              activeDot={{ r: 5 }}
              isAnimationActive={animate}
            />
          ))}
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

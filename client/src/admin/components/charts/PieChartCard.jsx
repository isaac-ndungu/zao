import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import ChartCard from './ChartCard'
import { CATEGORICAL_COLORS, CHART_DEFAULTS } from './chartTheme'
import { toPercent } from './chartUtils'

export default function PieChartCard({
  title, subtitle, action, emptyMessage,
  data = [], dataKey = 'value', categoryKey = 'name',
  innerRadius = 60, outerRadius = 100,
  height = 320, animate = true,
  colorMap = null, colors = CATEGORICAL_COLORS,
  showPercent = true,
}) {
  const empty = !data || data.length === 0
  const total = data.reduce((s, d) => s + (d[dataKey] || 0), 0)

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const entry = payload[0]
    return (
      <div style={CHART_DEFAULTS.tooltip.contentStyle}>
        <p className="text-body-md" style={{ color: entry.color }}>{entry.name}</p>
        <p className="font-label-md font-bold text-on-surface">
          {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          {showPercent && total > 0 ? ` (${toPercent(entry.value, total)})` : ''}
        </p>
      </div>
    )
  }

  const getColor = (entry, index) => {
    if (colorMap) return colorMap[entry[categoryKey]] || colors[index % colors.length]
    return colors[index % colors.length]
  }

  const renderLabel = ({ name, percent }) => {
    if (percent < 0.05) return null
    return `${(percent * 100).toFixed(0)}%`
  }

  return (
    <ChartCard title={title} subtitle={subtitle} action={action} empty={empty} emptyMessage={emptyMessage}>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey={dataKey}
            nameKey={categoryKey}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            label={renderLabel}
            labelLine={false}
            isAnimationActive={animate}
          >
            {data.map((entry, index) => (
              <Cell key={index} fill={getColor(entry, index)} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

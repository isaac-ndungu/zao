import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts'
import ChartCard from './ChartCard'
import { CATEGORICAL_COLORS, CHART_DEFAULTS } from './chartTheme'
import { toPercent } from './chartUtils'

export default function BarChartCard({
  title, subtitle, action, emptyMessage,
  data = [], dataKey = 'value', categoryKey = 'name',
  dataKeys = [], orientation = 'vertical', stacked = false, showPercent = false,
  colorMap = null, colors = CATEGORICAL_COLORS,
  height = 300, animate = true,
}) {
  const empty = !data || data.length === 0

  const total = showPercent ? data.reduce((s, d) => s + (d[dataKey] || 0), 0) : 0

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div style={CHART_DEFAULTS.tooltip.contentStyle}>
        <p className="font-label-md font-bold text-on-surface mb-1">{label}</p>
        {payload.map((entry, i) => (
          <p key={i} className="text-body-md" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            {showPercent && total > 0 ? ` (${toPercent(entry.value, total)})` : ''}
          </p>
        ))}
      </div>
    )
  }

  const getColor = (entry, index) => {
    if (colorMap) return colorMap[entry[categoryKey]] || colors[index % colors.length]
    return colors[index % colors.length]
  }

  return (
    <ChartCard title={title} subtitle={subtitle} action={action} empty={empty} emptyMessage={emptyMessage}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={orientation === 'horizontal' ? 'vertical' : 'horizontal'}
          margin={{ top: 4, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />
          {orientation === 'horizontal' ? (
            <>
              <XAxis type="number" tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey={categoryKey} tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} width={100} />
            </>
          ) : (
            <>
              <XAxis dataKey={categoryKey} tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: CHART_DEFAULTS.textColor }} axisLine={false} tickLine={false} />
            </>
          )}
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
          {stacked ? (
            dataKeys?.length ? dataKeys.map((key, i) => (
              <Bar key={key} dataKey={key} stackId="a" fill={colors[i % colors.length]} isAnimationActive={animate} radius={[0, 0, 0, 0]} />
            )) : null
          ) : dataKeys?.length ? dataKeys.map((key, i) => (
            <Bar key={key} dataKey={key} fill={colors[i % colors.length]} isAnimationActive={animate} radius={[4, 4, 0, 0]} maxBarSize={32} />
          )) : (
            <Bar dataKey={dataKey} isAnimationActive={animate} radius={[4, 4, 0, 0]} maxBarSize={32}>
              {data.map((entry, index) => (
                <Cell key={index} fill={getColor(entry, index)} />
              ))}
            </Bar>
          )}
          {!stacked && <Legend iconType="circle" wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

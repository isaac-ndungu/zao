import { BarChart, Bar, XAxis, ResponsiveContainer, Cell } from 'recharts'

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function getLast7Days() {
  const days = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    days.push(d.toISOString().slice(0, 10))
  }
  return days
}

function aggregateByDay(results) {
  const days = getLast7Days()
  const counts = Object.fromEntries(days.map((d) => [d, 0]))
  for (const item of results || []) {
    const day = item.created_at?.slice(0, 10)
    if (day && counts[day] !== undefined) counts[day]++
  }
  return days.map((dateStr) => {
    const dow = new Date(dateStr).getDay()
    return {
      date: dateStr,
      day: DAY_LABELS[dow === 0 ? 6 : dow - 1],
      count: counts[dateStr],
    }
  })
}

function trendPercent(data) {
  if (!data || data.length < 2) return null
  const recent = data.slice(-3).reduce((s, d) => s + d.count, 0)
  const prior = data.slice(0, 3).reduce((s, d) => s + d.count, 0)
  if (prior === 0) return null
  return Math.round(((recent - prior) / prior) * 100)
}

export default function SevenDayChart({ results }) {
  const data = aggregateByDay(results)
  const trend = trendPercent(data)

  if (!results || results.length === 0) return null

  const maxCount = Math.max(...data.map((d) => d.count), 1)

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-label-md text-on-surface-variant">This Week</span>
        {trend !== null && (
          <span className={`text-label-sm font-bold flex items-center gap-0.5 ${trend >= 0 ? 'text-primary' : 'text-error'}`}>
            <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
              {trend >= 0 ? 'trending_up' : 'trending_down'}
            </span>
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="day"
            tick={{ fontSize: 11, fill: 'currentColor' }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={28}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.count === maxCount ? '#0f5238' : '#2d6a4f'}
                opacity={entry.count === 0 ? 0.3 : 1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

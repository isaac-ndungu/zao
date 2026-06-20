import { useContext, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import { KpiSkeleton, CardSkeleton } from '../components/common/Skeleton'

const seasonColors = {
  LONG_RAINS: { bg: 'bg-primary-container', text: 'text-primary', label: 'Long Rains' },
  SHORT_RAINS: { bg: 'bg-primary-fixed', text: 'text-primary', label: 'Short Rains' },
  DRY_SEASON: { bg: 'bg-surface-container-high', text: 'text-on-surface-variant', label: 'Dry Season' },
}

function monthLabel(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

export default function SeasonalPatterns() {
  const { period } = useContext(AdminFilterContext)
  const { data, loading, error } = useApi(`/api/admin/analytics/seasonal/?period=${period}`)

  const series = data?.data?.series || []
  const summary = data?.data?.summary

  const productTypes = useMemo(() => {
    const types = new Set(series.map(s => s.product_type))
    return Array.from(types).sort()
  }, [series])

  const groupedByMonth = useMemo(() => {
    const map = {}
    series.forEach(s => {
      const key = s.month
      if (!map[key]) map[key] = { month: key, types: {}, totalKg: 0, season: s.season }
      map[key].types[s.product_type] = (map[key].types[s.product_type] || 0) + s.kg
      map[key].totalKg += s.kg
    })
    return Object.values(map).sort((a, b) => a.month.localeCompare(b.month))
  }, [series])

  const maxMonthKg = useMemo(() => Math.max(...groupedByMonth.map(m => m.totalKg), 1), [groupedByMonth])

  if (loading) {
    return <div><KpiSkeleton count={3} /><CardSkeleton /></div>
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load seasonal data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Seasonal Patterns</h2>
        <p className="text-on-surface-variant font-body-md">Annual production cycles, peak seasons, and monthly breakdown by product type.</p>
      </header>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KpiCard icon="bar_chart" label="Total Annual" value={summary.total_annual?.toLocaleString() || '-'} subvalue="kg" />
          <KpiCard icon="trending_up" label="Peak Month" value={summary.peak_month ? monthLabel(summary.peak_month) : '-'} subvalue={`${summary.peak_kg?.toLocaleString()} kg`} highlighted />
          <KpiCard icon="trending_down" label="Low Month" value={summary.low_month ? monthLabel(summary.low_month) : '-'} subvalue={`${summary.low_kg?.toLocaleString()} kg`} />
        </div>
      )}

      {groupedByMonth.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-6">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Volume by Product Type</h4>
          <div className="space-y-2">
            {groupedByMonth.map((m) => {
              const season = seasonColors[m.season] || seasonColors.DRY_SEASON
              return (
                <div key={m.month} className="flex items-center gap-3">
                  <div className="w-20 flex-shrink-0">
                    <span className="text-label-md font-medium text-on-surface-variant">{monthLabel(m.month)}</span>
                    <span className={`ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold ${season.bg} ${season.text}`}>{season.label}</span>
                  </div>
                  <div className="flex-1 h-7 bg-surface-container rounded-lg overflow-hidden flex">
                    {productTypes.map((pt, i) => {
                      const kg = m.types[pt] || 0
                      const pct = (kg / maxMonthKg) * 100
                      if (pct === 0) return null
                      const hue = (i * 60) % 360
                      return (
                        <div
                          key={pt}
                          className="h-full transition-all"
                          style={{ width: `${pct}%`, backgroundColor: `hsl(${hue}, 60%, 45%)` }}
                          title={`${pt}: ${kg.toLocaleString()} kg`}
                        />
                      )
                    })}
                  </div>
                  <span className="font-data-mono text-label-md text-on-surface-variant w-20 text-right">{m.totalKg?.toLocaleString()}</span>
                </div>
              )
            })}
          </div>
          <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-outline-variant/50">
            {productTypes.map((pt, i) => {
              const hue = (i * 60) % 360
              return (
                <span key={pt} className="flex items-center gap-1.5 text-label-md text-on-surface-variant">
                  <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: `hsl(${hue}, 60%, 45%)` }} />
                  {pt.toLowerCase()}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {series.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Detail</h4>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container">
                  <th className="px-3 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase">Month</th>
                  <th className="px-3 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase">Product</th>
                  <th className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Volume (kg)</th>
                  <th className="px-3 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase">Deliveries</th>
                  <th className="px-3 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase">Season</th>
                </tr>
              </thead>
              <tbody>
                {series.map((s, i) => {
                  const season = seasonColors[s.season] || seasonColors.DRY_SEASON
                  return (
                    <tr key={i} className={`border-b border-outline-variant/50 ${i % 2 === 0 ? 'bg-surface-container-lowest' : 'bg-surface-container'}`}>
                      <td className="px-3 py-2 text-body-md text-on-surface">{monthLabel(s.month)}</td>
                      <td className="px-3 py-2 text-body-md text-on-surface capitalize">{s.product_type?.toLowerCase()}</td>
                      <td className="px-3 py-2 text-right font-data-mono text-on-surface">{s.kg?.toLocaleString()}</td>
                      <td className="px-3 py-2 text-right font-data-mono text-on-surface">{s.delivery_count}</td>
                      <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded text-[10px] font-bold ${season.bg} ${season.text}`}>{season.label}</span></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {series.length === 0 && (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">calendar_month</span>
          <p>No seasonal data available for the selected period.</p>
        </div>
      )}
    </div>
  )
}

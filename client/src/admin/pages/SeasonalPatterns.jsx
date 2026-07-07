import { useContext, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import { KpiSkeleton } from '../components/common/Skeleton'
import AreaChartCard from '../components/charts/AreaChartCard'
import { normalizeStackedData } from '../components/charts/chartUtils'
import { CATEGORICAL_COLORS } from '../components/charts/chartTheme'

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
      if (!map[key]) map[key] = { month: key, monthLabel: monthLabel(key), totalKg: 0 }
      map[key][s.product_type] = (map[key][s.product_type] || 0) + s.kg
      map[key].totalKg += s.kg
    })
    return Object.values(map).sort((a, b) => a.month.localeCompare(b.month))
  }, [series])

  const chartData = useMemo(() => {
    return normalizeStackedData(groupedByMonth, productTypes)
  }, [groupedByMonth, productTypes])

  const areaConfig = useMemo(() => {
    return productTypes.map((pt, i) => ({
      key: pt,
      name: pt.toLowerCase(),
      color: CATEGORICAL_COLORS[i % CATEGORICAL_COLORS.length],
    }))
  }, [productTypes])

  if (loading) {
    return <div><KpiSkeleton count={3} /><div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-80 animate-pulse mt-6" /></div>
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <KpiCard icon="bar_chart" label="Total Annual" value={summary.total_annual?.toLocaleString() || '-'} subvalue="kg" />
          <KpiCard icon="trending_up" label="Peak Month" value={summary.peak_month ? monthLabel(summary.peak_month) : '-'} subvalue={`${summary.peak_kg?.toLocaleString()} kg`} highlighted />
          <KpiCard icon="trending_down" label="Low Month" value={summary.low_month ? monthLabel(summary.low_month) : '-'} subvalue={`${summary.low_kg?.toLocaleString()} kg`} />
        </div>
      )}

      {chartData.length > 0 ? (
        <AreaChartCard
          title="Monthly Volume by Product Type"
          data={chartData}
          xKey="monthLabel"
          areas={areaConfig}
          stacked
          height={380}
          emptyMessage="No seasonal data available for the selected period."
        />
      ) : (
        <div className="text-center py-12 text-on-surface-variant bg-surface-container-lowest border border-outline-variant rounded-xl">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">calendar_month</span>
          <p>No seasonal data available for the selected period.</p>
        </div>
      )}
    </div>
  )
}

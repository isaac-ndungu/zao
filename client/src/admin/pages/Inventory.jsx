import { useContext, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { exportCsv } from '../api/client'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import { KpiSkeleton } from '../components/common/Skeleton'
import PieChartCard from '../components/charts/PieChartCard'
import BarChartCard from '../components/charts/BarChartCard'

export default function Inventory() {
  const { period } = useContext(AdminFilterContext)
  const { data: prodData, loading, error } = useApi(`/api/admin/analytics/production/?period=${period}`)
  const { data: dashData } = useApi(`/api/admin/analytics/dashboard/?period=${period}`)

  const production = prodData?.data
  const inventory = dashData?.data?.inventory

  const gradePie = useMemo(() => {
    if (!production?.grade_distribution) return []
    return Object.entries(production.grade_distribution)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
      .map(([key, val]) => ({ name: key.toLowerCase(), value: Number(val) }))
  }, [production])

  const productPie = useMemo(() => {
    if (!production?.by_product_type) return []
    return Object.entries(production.by_product_type)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
      .map(([key, val]) => ({ name: key.toLowerCase(), value: Number(val) }))
  }, [production])

  const monthlyData = useMemo(() => {
    if (!production?.monthly_series) return []
    return Object.entries(production.monthly_series)
      .slice(-12)
      .map(([month, types]) => ({
        month,
        kg: Object.values(types).reduce((s, v) => s + v, 0),
      }))
  }, [production])

  if (loading) {
    return <div><KpiSkeleton count={4} /><div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-80 animate-pulse mt-6" /></div>
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load inventory data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Inventory</h2>
        <p className="text-on-surface-variant font-body-md">Production volumes, stock levels, and grade distribution.</p>
      </header>

      <FilterBar
        search={''}
        onSearchChange={() => {}}
        placeholder=""
        filters={[]}
        filterValues={{}}
        onFilterChange={() => {}}
        onClear={() => {}}
        onExport={() => { const p = new URLSearchParams(); p.set('period', period); p.set('export', 'csv'); exportCsv(`/api/admin/analytics/production/?${p}`) }}
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard icon="inventory" label="Running Balance" value={inventory?.running_balance?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="arrow_downward" label="Total In" value={inventory?.total_in?.toLocaleString() || production?.total_kg?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="arrow_upward" label="Total Out" value={inventory?.total_out?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="fact_check" label="Total Deliveries" value={production?.delivery_count || 0} />
      </div>

      {production && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {gradePie.length > 0 && (
            <PieChartCard
              title="Grade Distribution"
              data={gradePie}
              dataKey="value"
              nameKey="name"
              height={300}
              showPercent
              emptyMessage="No grade data available."
            />
          )}
          {productPie.length > 0 && (
            <PieChartCard
              title="By Product Type"
              data={productPie}
              dataKey="value"
              nameKey="name"
              height={300}
              showPercent
              emptyMessage="No product data available."
            />
          )}
        </div>
      )}

      {monthlyData.length > 0 && (
        <BarChartCard
          title="Monthly Production"
          data={monthlyData}
          categoryKey="month"
          dataKeys={['kg']}
          height={350}
          emptyMessage="No monthly production data available."
        />
      )}

      {!production && (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">inventory_2</span>
          <p>No inventory data available for the selected period.</p>
        </div>
      )}
    </div>
  )
}

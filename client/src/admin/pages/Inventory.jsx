import { useContext, useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import { KpiSkeleton, CardSkeleton } from '../components/common/Skeleton'

export default function Inventory() {
  const { period } = useContext(AdminFilterContext)
  const { data: prodData, loading, error } = useApi(`/api/admin/analytics/production/?period=${period}`)
  const { data: dashData } = useApi(`/api/admin/analytics/dashboard/?period=${period}`)

  const production = prodData?.data
  const inventory = dashData?.data?.inventory

  const gradeDist = useMemo(() => {
    if (!production?.grade_distribution) return []
    return Object.entries(production.grade_distribution).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a)
  }, [production])

  const productBreakdown = useMemo(() => {
    if (!production?.by_product_type) return []
    return Object.entries(production.by_product_type).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a)
  }, [production])

  const totalGrade = gradeDist.reduce((s, [, v]) => s + v, 0)

  if (loading) {
    return <div><KpiSkeleton count={4} /><CardSkeleton /></div>
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
        onExport={() => { const p = new URLSearchParams(); p.set('period', period); p.set('export', 'csv'); window.open(`/api/admin/analytics/production/?${p}`, '_blank') }}
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KpiCard icon="inventory" label="Running Balance" value={inventory?.running_balance?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="arrow_downward" label="Total In" value={inventory?.total_in?.toLocaleString() || production?.total_kg?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="arrow_upward" label="Total Out" value={inventory?.total_out?.toLocaleString() || '-'} subvalue="kg" />
        <KpiCard icon="fact_check" label="Total Deliveries" value={production?.delivery_count || 0} />
      </div>

      {production && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Grade Distribution */}
          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
            <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Grade Distribution</h4>
            {gradeDist.length === 0 ? (
              <p className="text-on-surface-variant text-body-md">No grade data available.</p>
            ) : (
              <div className="space-y-3">
                {gradeDist.map(([grade, count]) => {
                  const pct = totalGrade > 0 ? (count / totalGrade) * 100 : 0
                  return (
                    <div key={grade}>
                      <div className="flex justify-between text-label-md font-medium mb-1">
                        <span className="capitalize">{grade.toLowerCase()}</span>
                        <span className="font-data-mono text-on-surface-variant">{count?.toLocaleString()} kg</span>
                      </div>
                      <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Product Type Breakdown */}
          <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
            <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">By Product Type</h4>
            {productBreakdown.length === 0 ? (
              <p className="text-on-surface-variant text-body-md">No product data available.</p>
            ) : (
              <div className="space-y-4">
                {productBreakdown.map(([type, qty]) => (
                  <div key={type} className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                      <span className="capitalize font-medium">{type.toLowerCase()}</span>
                    </div>
                    <span className="font-data-mono text-on-surface">{qty?.toLocaleString()} kg</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Monthly Series (simplified) */}
      {production?.monthly_series && production.monthly_series.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-6">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Production</h4>
          <div className="space-y-2">
            {production.monthly_series.slice(-12).map((month) => (
              <div key={month.month} className="flex items-center gap-4">
                <span className="text-label-md font-medium text-on-surface-variant w-24">{month.month}</span>
                <div className="flex-1 h-6 bg-surface-container rounded-lg overflow-hidden flex">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${Math.min(100, (month.kg / Math.max(...production.monthly_series.map(m => m.kg))) * 100)}%` }}
                  />
                </div>
                <span className="font-data-mono text-label-md text-on-surface-variant w-20 text-right">
                  {month.kg?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
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

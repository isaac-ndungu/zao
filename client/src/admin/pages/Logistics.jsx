import { useContext, useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { exportCsv } from '../api/client'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import { KpiSkeleton, CardSkeleton } from '../components/common/Skeleton'
import { Link } from 'react-router-dom'

export default function Logistics() {
  const { period } = useContext(AdminFilterContext)
  const [view, setView] = useState('operations')

  const { data: opsData, loading, error } = useApi(`/api/admin/analytics/operations/?period=${period}`)
  const { data: deliveriesData } = useApi(`/api/admin/deliveries/?page=1&page_size=5&ordering=-date_delivered`)

  const ops = opsData?.data

  const shiftBreakdown = useMemo(() => {
    if (!ops?.by_shift) return []
    return Object.entries(ops.by_shift).filter(([, v]) => v > 0)
  }, [ops])

  const totalShift = shiftBreakdown.reduce((s, [, v]) => s + v, 0)

  const topGraders = useMemo(() => {
    if (!ops?.top_graders) return []
    return ops.top_graders.slice(0, 5)
  }, [ops])

  const rejectionReasons = useMemo(() => {
    if (!ops?.rejection_reasons) return []
    return Object.entries(ops.rejection_reasons).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a)
  }, [ops])

  const maxRejection = rejectionReasons.length > 0 ? Math.max(...rejectionReasons.map(([, v]) => v)) : 1

  if (loading) {
    return <div><KpiSkeleton count={3} /><CardSkeleton /></div>
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load logistics data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-headline-lg text-display-md text-primary">Logistics</h2>
          <div className="flex gap-1 bg-surface-container rounded-lg p-0.5">
            <button onClick={() => setView('operations')} className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${view === 'operations' ? 'bg-surface-container-lowest shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
              Operations
            </button>
            <button onClick={() => setView('deliveries')} className={`px-3 py-1.5 rounded-lg text-label-md font-bold transition-colors ${view === 'deliveries' ? 'bg-surface-container-lowest shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
              Recent Deliveries
            </button>
          </div>
        </div>
        <p className="text-on-surface-variant font-body-md">Operations hub — shifts, graders, and delivery logistics.</p>
      </header>

      <FilterBar
        search={''}
        onSearchChange={() => {}}
        placeholder=""
        filters={[]}
        filterValues={{}}
        onFilterChange={() => {}}
        onClear={() => {}}
        onExport={() => { const p = new URLSearchParams(); p.set('period', period); p.set('export', 'csv'); exportCsv(`/api/admin/analytics/operations/?${p}`) }}
      />

      {view === 'operations' && ops ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <KpiCard icon="local_shipping" label="Total Deliveries" value={ops.total_deliveries || 0} />
            <KpiCard icon="casino" label="Grade Overrides" value={ops.grade_overrides || 0} />
            <KpiCard icon="speed" label="Avg Daily Intake" value={ops.avg_daily_intake ? `${ops.avg_daily_intake.toLocaleString()} kg` : '-'} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Shift Breakdown */}
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Volume by Shift</h4>
              {shiftBreakdown.length === 0 ? (
                <p className="text-on-surface-variant text-body-md">No shift data available.</p>
              ) : (
                <div className="space-y-3">
                  {shiftBreakdown.map(([shift, count]) => {
                    const pct = totalShift > 0 ? (count / totalShift) * 100 : 0
                    return (
                      <div key={shift}>
                        <div className="flex justify-between text-label-md font-medium mb-1">
                          <span className="capitalize">{shift.toLowerCase()}</span>
                          <span className="font-data-mono text-on-surface-variant">{count}</span>
                        </div>
                        <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-secondary" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Top Graders */}
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Top Graders</h4>
              {topGraders.length === 0 ? (
                <p className="text-on-surface-variant text-body-md">No grader data available.</p>
              ) : (
                <div className="space-y-3">
                  {topGraders.map((grader, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-data-mono text-[11px] font-bold">
                          {i + 1}
                        </span>
                        <span className="font-medium capitalize">
                          {typeof grader === 'string' ? grader : grader.name || grader.grader_name || `Grader ${i + 1}`}
                        </span>
                      </div>
                      <span className="font-data-mono text-on-surface-variant">
                        {typeof grader === 'number' ? grader : grader.count || grader.score || 0} graded
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Rejection Reasons */}
          {rejectionReasons.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl mb-6">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Rejection Reasons</h4>
              <div className="space-y-3">
                {rejectionReasons.map(([reason, count]) => (
                  <div key={reason}>
                    <div className="flex justify-between text-label-md font-medium mb-1">
                      <span className="capitalize">{reason.replace(/_/g, ' ').toLowerCase()}</span>
                      <span className="font-data-mono text-on-surface-variant">{count}</span>
                    </div>
                    <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-error-container" style={{ width: `${(count / maxRejection) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Monthly Volume */}
          {ops?.monthly_volume && ops.monthly_volume.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
              <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Monthly Volume</h4>
              <div className="space-y-2">
                {ops.monthly_volume.slice(-12).map((m) => (
                  <div key={m.month} className="flex items-center gap-4">
                    <span className="text-label-md font-medium text-on-surface-variant w-24">{m.month}</span>
                    <div className="flex-1 h-6 bg-surface-container rounded-lg overflow-hidden">
                      <div
                        className="h-full bg-primary-fixed transition-all"
                        style={{ width: `${Math.min(100, (m.kg / Math.max(...ops.monthly_volume.map(x => x.kg))) * 100)}%` }}
                      />
                    </div>
                    <span className="font-data-mono text-label-md text-on-surface-variant w-20 text-right">
                      {m.kg?.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : view === 'operations' && !ops ? (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">local_shipping</span>
          <p>No operations data available for the selected period.</p>
        </div>
      ) : (
        /* Recent Deliveries view */
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between">
            <h4 className="font-headline-sm text-headline-sm text-on-surface">Recent Deliveries</h4>
            <Link to="/admin/receipts" className="text-label-md font-bold text-primary hover:underline">View All</Link>
          </div>
          {deliveriesData?.results?.length > 0 ? (
            <div className="divide-y divide-outline-variant/50">
              {deliveriesData.results.map((d) => (
                <div key={d.id} className="px-6 py-4 flex items-center justify-between hover:bg-surface-container transition-colors">
                  <div>
                    <p className="font-data-mono text-primary text-body-md">{d.batch_id}</p>
                    <p className="text-label-md text-on-surface-variant">{d.farmer_name} · {d.product_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-data-mono text-body-md text-on-surface">{d.quantity_kg?.toLocaleString()} kg</p>
                    <span className={`text-[11px] font-bold uppercase ${d.status === 'REJECTED' ? 'text-error' : 'text-primary'}`}>{d.status}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-on-surface-variant">No recent deliveries.</div>
          )}
        </div>
      )}
    </div>
  )
}

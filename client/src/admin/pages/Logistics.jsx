import { useContext, useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { exportCsv } from '../api/client'
import { AdminFilterContext } from '../contexts/AdminFilterContext'
import KpiCard from '../components/common/KpiCard'
import FilterBar from '../components/common/FilterBar'
import { KpiSkeleton } from '../components/common/Skeleton'
import { Link } from 'react-router-dom'
import PieChartCard from '../components/charts/PieChartCard'
import BarChartCard from '../components/charts/BarChartCard'
import LineChartCard from '../components/charts/LineChartCard'

export default function Logistics() {
  const { period } = useContext(AdminFilterContext)
  const [view, setView] = useState('operations')

  const { data: opsData, loading, error } = useApi(`/api/admin/analytics/operations/?period=${period}`)
  const { data: deliveriesData } = useApi(`/api/admin/deliveries/?page=1&page_size=5&ordering=-date_delivered`)

  const ops = opsData?.data

  const shiftPie = useMemo(() => {
    if (!ops?.by_shift) return []
    return Object.entries(ops.by_shift)
      .filter(([, v]) => v > 0)
      .map(([key, val]) => ({ name: key.toLowerCase(), value: Number(val) }))
  }, [ops])

  const rejectionData = useMemo(() => {
    if (!ops?.rejection_reasons) return []
    return Object.entries(ops.rejection_reasons)
      .filter(([, v]) => v > 0)
      .sort(([, a], [, b]) => b - a)
      .map(([key, val]) => ({
        reason: key.replace(/_/g, ' ').toLowerCase(),
        count: Number(val),
      }))
  }, [ops])

  const graderData = useMemo(() => {
    if (!ops?.top_graders) return []
    return ops.top_graders.slice(0, 5).map((g, i) => ({
      name: g.email || g.name || `Grader ${i + 1}`,
      graded: g.count || g.score || 0,
    }))
  }, [ops])

  const monthlyVolume = useMemo(() => {
    if (!ops?.monthly_volume) return []
    return Object.entries(ops.monthly_volume)
      .slice(-12)
      .map(([month, vals]) => ({
        month,
        kg: vals.kg,
      }))
  }, [ops])

  if (loading) {
    return <div><KpiSkeleton count={3} /><div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl h-80 animate-pulse mt-6" /></div>
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <KpiCard icon="local_shipping" label="Total Deliveries" value={ops.total_deliveries || 0} />
            <KpiCard icon="casino" label="Grade Overrides" value={ops.grade_overrides || 0} />
            <KpiCard icon="speed" label="Avg Daily Intake" value={ops.avg_daily_intake ? `${ops.avg_daily_intake.toLocaleString()} kg` : '-'} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {shiftPie.length > 0 && (
              <PieChartCard
                title="Volume by Shift"
                data={shiftPie}
                dataKey="value"
                nameKey="name"
                height={280}
                showPercent
                emptyMessage="No shift data available."
              />
            )}
            {graderData.length > 0 && (
              <BarChartCard
                title="Top Graders"
                data={graderData}
                categoryKey="name"
                dataKeys={['graded']}
                height={280}
                emptyMessage="No grader data available."
              />
            )}
          </div>

          {rejectionData.length > 0 && (
            <BarChartCard
              title="Rejection Reasons"
              data={rejectionData}
              categoryKey="reason"
              dataKeys={['count']}
              layout="horizontal"
              height={280}
              emptyMessage="No rejection data available."
            />
          )}

          {monthlyVolume.length > 0 && (
            <LineChartCard
              title="Monthly Volume"
              data={monthlyVolume}
              xKey="month"
              lines={[
                { key: 'kg', name: 'Volume (kg)', color: '#2563eb' },
              ]}
              yFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              height={300}
              emptyMessage="No monthly volume data available."
            />
          )}
        </>
      ) : view === 'operations' && !ops ? (
        <div className="text-center py-12 text-on-surface-variant">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant">local_shipping</span>
          <p>No operations data available for the selected period.</p>
        </div>
      ) : (
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

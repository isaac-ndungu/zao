import { useApi } from '../../admin/hooks/useApi'
import KpiCard from '../../admin/components/common/KpiCard'
import { KpiSkeleton } from '../../admin/components/common/Skeleton'

function formatKes(n) {
  if (!n || n === 0) return 'KES 0'
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`
  return `KES ${Number(n).toLocaleString()}`
}

function formatNumber(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n || 0)
}

export default function AuditorProduction() {
  const { data: prodData, loading } = useApi('/api/analytics/production/')

  const prod = prodData?.data || prodData || {}

  if (loading) {
    return (
      <div>
        <header className="mb-8"><h2 className="font-headline-lg text-display-md text-primary mb-1">Production Overview</h2><p className="text-on-surface-variant font-body-md">Deliveries & produce statistics</p></header>
        <KpiSkeleton count={6} />
      </div>
    )
  }

  const productBreakdown = prod.product_breakdown || []
  const deliveriesByRoute = prod.deliveries_by_route || []
  /* unused: qualityStats */

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Production Overview</h2>
        <p className="text-on-surface-variant font-body-md">Deliveries & produce statistics</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard icon="local_shipping" label="Total Deliveries" value={formatNumber(prod.total_deliveries)} />
        <KpiCard icon="scale" label="Total Quantity" value={prod.total_kg ? `${formatNumber(prod.total_kg)} kg` : '-'} />
        <KpiCard icon="people" label="Active Farmers" value={formatNumber(prod.active_farmers)} />
        <KpiCard icon="star" label="Avg Grade" value={prod.avg_grade || '-'} />
      </div>

      {productBreakdown.length > 0 && (
        <div className="mb-8">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Product Breakdown</h3>
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container">
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Product Type</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Quantity (kg)</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Volume (L)</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Deliveries</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Total Value</th>
                </tr>
              </thead>
              <tbody>
                {productBreakdown.map((p, i) => (
                  <tr key={i} className="border-b border-outline-variant/50 last:border-0 hover:bg-surface-container transition-colors">
                    <td className="px-6 py-3 text-body-md font-medium">{p.product_type || p.name || p.type}</td>
                    <td className="px-6 py-3 text-body-md">{p.total_kg ? formatNumber(p.total_kg) : '-'}</td>
                    <td className="px-6 py-3 text-body-md">{p.total_volume ? formatNumber(p.total_volume) : '-'}</td>
                    <td className="px-6 py-3 text-body-md">{p.delivery_count || 0}</td>
                    <td className="px-6 py-3 text-body-md">{p.total_value ? formatKes(p.total_value) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {deliveriesByRoute.length > 0 && (
        <div>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Deliveries by Route</h3>
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container">
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Route</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Deliveries</th>
                  <th className="px-6 py-3 text-label-md font-bold text-on-surface">Total (kg)</th>
                </tr>
              </thead>
              <tbody>
                {deliveriesByRoute.map((r, i) => (
                  <tr key={i} className="border-b border-outline-variant/50 last:border-0 hover:bg-surface-container transition-colors">
                    <td className="px-6 py-3 text-body-md">{r.name || r.route || `Route #${i + 1}`}</td>
                    <td className="px-6 py-3 text-body-md">{r.count || r.delivery_count || 0}</td>
                    <td className="px-6 py-3 text-body-md">{r.total_kg ? formatNumber(r.total_kg) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

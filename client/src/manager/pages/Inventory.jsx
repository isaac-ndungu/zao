import { useApi } from '../../admin/hooks/useApi'
import StatusBadge from '../../admin/components/common/StatusBadge'
import ErrorState from '../../shared/components/ErrorState'

export default function Inventory() {
  const { data, loading, error, refetch } = useApi('/api/stock/')
  const stockItems = data?.results || []

  if (loading) {
    return <div className="p-8 text-center text-on-surface-variant">Loading stock…</div>
  }
  if (error) {
    return <ErrorState message={error} action={{ label: 'Retry', onClick: refetch }} />
  }

  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h2 className="text-3xl font-bold text-on-surface mb-1">Inventory</h2>
        <p className="text-sm text-on-surface-variant">
          {stockItems.length} stock line{stockItems.length === 1 ? '' : 's'} — current sellable stock per product &amp; grade.
        </p>
      </header>

      {stockItems.length === 0 ? (
        <div className="text-center py-12 text-on-surface-variant bg-surface-container-lowest border border-outline-variant rounded-xl">
          <span className="material-symbols-outlined text-[48px] block mb-2 text-outline-variant" aria-hidden="true">inventory_2</span>
          <p className="text-on-surface mb-2">No stock recorded yet.</p>
          <p className="text-sm">Stock is created automatically when deliveries are graded. Record deliveries to see inventory here.</p>
        </div>
      ) : (
        <section className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-outline-variant bg-surface-container">
            <h3 className="font-headline-sm text-title-md text-on-surface">Total Stock</h3>
            <p className="text-label-md text-on-surface-variant">
              The &ldquo;proper inventory&rdquo; — current sellable stock per product &amp; grade.
            </p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-surface-container border-b border-outline-variant">
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Product</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Grade</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Unit</th>
                <th scope="col" className="px-4 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Available</th>
                <th scope="col" className="px-4 py-2 text-right text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Low&nbsp;@</th>
                <th scope="col" className="px-4 py-2 text-left text-label-md font-bold text-on-surface-variant uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {stockItems.map((s) => {
                const low = Number(s.quantity_available) <= Number(s.low_stock_threshold)
                return (
                  <tr key={s.id} className="border-b border-outline-variant/50 hover:bg-surface-container">
                    <td className="px-4 py-2 text-body-md text-on-surface">{s.product_type}</td>
                    <td className="px-4 py-2 text-body-md text-on-surface">{s.grade || '-'}</td>
                    <td className="px-4 py-2 text-body-md text-on-surface">{s.unit}</td>
                    <td className="px-4 py-2 text-body-md text-on-surface text-right font-bold">{Number(s.quantity_available).toLocaleString()}</td>
                    <td className="px-4 py-2 text-body-md text-on-surface-variant text-right">{Number(s.low_stock_threshold).toLocaleString()}</td>
                    <td className="px-4 py-2">
                      {low
                        ? <StatusBadge status="error" label="Low" />
                        : <StatusBadge status="success" label="OK" />}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}

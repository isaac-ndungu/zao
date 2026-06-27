import { useState } from 'react'
import { apiFetch } from '../../admin/api/client'
import { useToast } from '../../admin/contexts/ToastContext'

function formatKes(n) {
  if (!n || n === 0) return 'KES 0'
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`
  return `KES ${Number(n).toLocaleString()}`
}

const currentYear = new Date().getFullYear()

export default function ExternalFinancialStatements() {
  const { showToast } = useToast()
  const [year, setYear] = useState(currentYear)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingKRA, setLoadingKRA] = useState(false)

  const handleFetchAnnual = async () => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/statements/annual-report/?year=${year}`)
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to fetch report') }
      const data = await res.json()
      setReport(data)
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
    finally { setLoading(false) }
  }

  const handleDownloadKRA = async () => {
    setLoadingKRA(true)
    try {
      const res = await apiFetch(`/api/statements/kra-report/?year=${year}&download=true`)
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Download failed') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kra_wht_report_${year}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      showToast({ type: 'success', message: 'KRA report downloaded.' })
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
    finally { setLoadingKRA(false) }
  }

  const handleDownloadSeason = async () => {
    setLoadingKRA(true)
    try {
      const res = await apiFetch(`/api/statements/report/?cycle_id=latest&download=true`)
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Download failed') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `season_report_${year}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      showToast({ type: 'success', message: 'Season report downloaded.' })
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
    finally { setLoadingKRA(false) }
  }

  const summary = report?.summary || {}
  const farmerSummaries = report?.farmer_summaries || []

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Financial Statements</h2>
        <p className="text-on-surface-variant font-body-md">Annual financial reports and statutory filings</p>
      </header>

      <div className="flex flex-wrap gap-4 items-center mb-8">
        <div className="flex items-center gap-2">
          <label className="text-label-md text-on-surface-variant">Financial Year</label>
          <select value={year} onChange={(e) => setYear(Number(e.target.value))} className="px-3 py-2 border border-outline-variant rounded-lg text-body-md bg-surface-container">
            {Array.from({ length: 5 }, (_, i) => currentYear - i).map((y) => (
              <option key={y} value={y}>{y}/{y + 1}</option>
            ))}
          </select>
        </div>
        <button onClick={handleFetchAnnual} disabled={loading} className="px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 disabled:opacity-50 transition-colors">
          {loading ? 'Loading...' : 'View Annual Report'}
        </button>
        <button onClick={handleDownloadKRA} disabled={loadingKRA} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors disabled:opacity-50">
          {loadingKRA ? '...' : 'Download KRA Report'}
        </button>
        <button onClick={handleDownloadSeason} disabled={loadingKRA} className="px-4 py-2 border border-outline-variant rounded-lg text-label-md font-bold hover:bg-surface-container transition-colors disabled:opacity-50">
          {loadingKRA ? '...' : 'Download Season Report'}
        </button>
      </div>

      {report && (
        <div className="space-y-6">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">{report.financial_year} Annual Report</h3>
            <p className="text-body-md text-on-surface-variant mb-4">
              Period: {report.period?.start} – {report.period?.end}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-surface-container rounded-xl p-4">
                <p className="text-label-md text-on-surface-variant">Total Revenue</p>
                <p className="font-headline-sm text-headline-sm text-primary">{formatKes(summary.total_revenue)}</p>
              </div>
              <div className="bg-surface-container rounded-xl p-4">
                <p className="text-label-md text-on-surface-variant">Total Farmer Payments</p>
                <p className="font-headline-sm text-headline-sm text-primary">{formatKes(summary.total_farmer_payments)}</p>
              </div>
              <div className="bg-surface-container rounded-xl p-4">
                <p className="text-label-md text-on-surface-variant">WHT Held</p>
                <p className="font-headline-sm text-headline-sm text-primary">{formatKes(summary.total_withholding_tax_held)}</p>
              </div>
              <div className="bg-surface-container rounded-xl p-4">
                <p className="text-label-md text-on-surface-variant">Active Cycles</p>
                <p className="font-headline-sm text-headline-sm text-on-surface">{summary.cycle_count || 0}</p>
              </div>
            </div>
          </div>

          {summary.total_produce_received && Object.keys(summary.total_produce_received).length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Produce Received</h3>
              <div className="overflow-hidden rounded-xl border border-outline-variant">
                <table className="w-full text-left">
                  <thead className="bg-surface-container">
                    <tr>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Type</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Total (kg)</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Volume (L)</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Deliveries</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(summary.total_produce_received).map(([type, data]) => (
                      <tr key={type} className="border-t border-outline-variant/50">
                        <td className="px-4 py-3 text-body-md font-medium">{type}</td>
                        <td className="px-4 py-3 text-body-md">{data.total_kg || '-'}</td>
                        <td className="px-4 py-3 text-body-md">{data.total_volume || '-'}</td>
                        <td className="px-4 py-3 text-body-md">{data.delivery_count || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {farmerSummaries.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Farmer Payment Summary ({farmerSummaries.length})</h3>
              <div className="overflow-x-auto rounded-xl border border-outline-variant">
                <table className="w-full text-left">
                  <thead className="bg-surface-container">
                    <tr>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Member No.</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Farmer Name</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Quantity</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Gross</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Deductions</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">Net</th>
                      <th className="px-4 py-3 text-label-md font-bold text-on-surface">WHT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {farmerSummaries.map((fs) => (
                      <tr key={fs.farmer_id} className="border-t border-outline-variant/50">
                        <td className="px-4 py-3 text-body-md">{fs.member_number || '-'}</td>
                        <td className="px-4 py-3 text-body-md font-medium">{fs.farmer_name || '-'}</td>
                        <td className="px-4 py-3 text-body-md">{fs.total_quantity ? `${fs.total_quantity} kg` : '-'}</td>
                        <td className="px-4 py-3 text-body-md">{formatKes(fs.total_gross)}</td>
                        <td className="px-4 py-3 text-body-md">{formatKes(fs.total_deductions)}</td>
                        <td className="px-4 py-3 text-body-md font-bold">{formatKes(fs.total_net)}</td>
                        <td className="px-4 py-3 text-body-md">{formatKes(fs.total_withholding_tax)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {!report && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant/40 mb-4">finance</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">Select a financial year</h3>
          <p className="text-body-md text-on-surface-variant">Choose a year above and click "View Annual Report" to see the financial statements.</p>
        </div>
      )}
    </div>
  )
}

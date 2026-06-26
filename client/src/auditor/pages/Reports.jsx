import { useState } from 'react'
import { useToast } from '../../admin/contexts/ToastContext'
import { apiFetch } from '../../admin/api/client'

const reportCards = [
  {
    title: 'Comprehensive Season Report',
    desc: 'Full season financial including payouts, deductions, and loan recovery data',
    icon: 'description',
    endpoint: '/api/reports/season/',
    filename: 'season_report.pdf',
  },
  {
    title: 'Annual Financial Statement',
    desc: 'Audit-ready annual statement with revenue, expenses, and net payouts',
    icon: 'finance',
    endpoint: '/api/reports/annual/',
    filename: 'annual_statement.pdf',
  },
  {
    title: 'KRA Withholding Tax Report',
    desc: 'WHT schedule per farmer for KRA compliance filing',
    icon: 'receipt_long',
    endpoint: '/api/reports/kra/',
    filename: 'kra_wht_report.pdf',
  },
  {
    title: 'Farmer Payment Statement',
    desc: 'Per-farmer breakdown of gross pay, deductions, and net disbursed',
    icon: 'fact_check',
    endpoint: '/api/reports/farmer-payments/',
    filename: 'farmer_payments.pdf',
  },
  {
    title: 'Loan Portfolio Summary',
    desc: 'Outstanding loans, repayment rates, and default analysis',
    icon: 'account_balance_wallet',
    endpoint: '/api/reports/loans/',
    filename: 'loan_portfolio.pdf',
  },
  {
    title: 'Deductions Audit Trail',
    desc: 'All deductions by type, farmer, and cycle for audit review',
    icon: 'account_tree',
    endpoint: '/api/reports/deductions/',
    filename: 'deductions_audit.pdf',
  },
]

export default function AuditorReports() {
  const { showToast } = useToast()
  const [loading, setLoading] = useState(null)

  const handleDownload = async (card) => {
    setLoading(card.endpoint)
    try {
      const res = await apiFetch(card.endpoint)
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Download failed') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = card.filename
      a.click()
      URL.revokeObjectURL(url)
      showToast({ type: 'success', message: `${card.title} downloaded.` })
    } catch (err) {
      showToast({ type: 'error', message: err.message })
    }
    finally { setLoading(null) }
  }

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Reports</h2>
        <p className="text-on-surface-variant font-body-md">Download financial and compliance reports as PDF</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {reportCards.map((card) => (
          <div key={card.endpoint} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-secondary-container flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-secondary">{card.icon}</span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">{card.title}</h3>
            <p className="text-body-md text-on-surface-variant mb-6 leading-relaxed">{card.desc}</p>
            <button
              onClick={() => handleDownload(card)}
              disabled={loading === card.endpoint}
              className="w-full px-4 py-2 rounded-lg bg-primary text-on-primary text-label-md font-bold hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {loading === card.endpoint ? 'Downloading...' : 'Download PDF'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

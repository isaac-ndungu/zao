import { useNavigate } from 'react-router-dom'
import { exportCsv } from '../../admin/api/client'

const reportCards = [
  { icon: 'local_shipping', label: 'Deliveries Report', desc: 'Export deliveries data as CSV', endpoint: '/api/deliveries/?export=csv' },
  { icon: 'payments', label: 'Payment Cycles Export', desc: 'Export payment cycle data', endpoint: '/api/payment-engine/?export=csv' },
  { icon: 'point_of_sale', label: 'Sales Export', desc: 'Export sales records as CSV', endpoint: '/api/sales/?export=csv' },
  { icon: 'money_off', label: 'Deductions Export', desc: 'Export deductions data as CSV', endpoint: '/api/deductions/?export=csv' },
  { icon: 'account_balance_wallet', label: 'Loans Export', desc: 'Export loan records as CSV', endpoint: '/api/loans/?export=csv' },
  { icon: 'account_balance', label: 'Disbursements Export', desc: 'Export disbursement batches', endpoint: '/api/disbursements/?format=csv' },
]

const navCards = [
  { icon: 'inventory_2', label: 'Inventory Summary', desc: 'View inventory levels and alerts', to: '/manager/inventory' },
  { icon: 'payments', label: 'Payment Cycles', desc: 'View and manage payment cycles', to: '/manager/cycles' },
  { icon: 'point_of_sale', label: 'Sales & Buyers', desc: 'View sales records', to: '/manager/sales' },
  { icon: 'account_balance_wallet', label: 'Loans', desc: 'View loan portfolio', to: '/manager/loans' },
]

export default function Reports() {
  const navigate = useNavigate()

  return (
    <div>
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Reports</h2>
        <p className="text-on-surface-variant font-body-md">Export data and view summaries</p>
      </header>

      <section className="mb-8">
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Quick Navigation</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {navCards.map((card) => (
            <button
              key={card.to}
              onClick={() => navigate(card.to)}
              className="text-left bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-high transition-colors"
            >
              <span className="material-symbols-outlined text-primary text-[32px] mb-2">{card.icon}</span>
              <h4 className="font-headline-sm text-title-md text-on-surface mb-1">{card.label}</h4>
              <p className="text-body-md text-on-surface-variant">{card.desc}</p>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Data Exports</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reportCards.map((card) => (
            <button
              key={card.label}
              onClick={() => exportCsv(card.endpoint)}
              className="text-left bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-high transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="material-symbols-outlined text-primary">{card.icon}</span>
                <h4 className="font-headline-sm text-title-md text-on-surface">{card.label}</h4>
              </div>
              <p className="text-body-md text-on-surface-variant mb-3">{card.desc}</p>
              <span className="text-label-md font-bold text-primary flex items-center gap-1">
                <span className="material-symbols-outlined text-[16px]">download</span>Download CSV
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}

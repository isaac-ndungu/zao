import { useLocation, useNavigate } from 'react-router-dom'
import { t } from '../i18n'

const tabs = [
  { path: '/farmer/dashboard', icon: 'home', labelKey: 'dashboard' },
  { path: '/farmer/deliveries', icon: 'receipt_long', labelKey: 'deliveries' },
  { path: '/farmer/payments', icon: 'payments', labelKey: 'payments' },
  { path: '/farmer/grades', icon: 'grade', labelKey: 'grades' },
    { path: '/farmer/loans', icon: 'account_balance', labelKey: 'loans' },   
  { path: '/farmer/profile', icon: 'person', labelKey: 'profile' },
]

export default function BottomNav() {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  return (
    <nav aria-label="Main navigation" className="fixed bottom-0 left-0 right-0 bg-surface-container border-t border-outline-variant flex justify-around py-1.5 z-30 max-w-lg mx-auto">
      {tabs.map((tab) => {
        const active = pathname === tab.path || (tab.path !== '/farmer/dashboard' && pathname.startsWith(tab.path))
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={`flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg border-none bg-transparent text-[11px] font-medium min-w-[56px] min-h-[44px] transition-colors ${active ? 'text-primary' : 'text-on-surface-variant'}`}
          >
            <span className="material-symbols-outlined" aria-hidden="true">{tab.icon}</span>
            <span>{t(tab.labelKey)}</span>
          </button>
        )
      })}
    </nav>
  )
}

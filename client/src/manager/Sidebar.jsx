import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'

const navItems = [
  { to: '/manager/dashboard', icon: 'dashboard', label: 'Dashboard' },
  { to: '/manager/farmers', icon: 'agriculture', label: 'Farmers' },
  { to: '/manager/users', icon: 'group', label: 'Staff' },
  { to: '/manager/deliveries', icon: 'local_shipping', label: 'Deliveries' },
  { to: '/manager/grading', icon: 'grading', label: 'Grading Queue' },
  { to: '/manager/cycles', icon: 'payments', label: 'Payment Cycles' },
  { to: '/manager/disbursements', icon: 'account_balance', label: 'Disbursements' },
  { to: '/manager/loans', icon: 'account_balance_wallet', label: 'Loans' },
  { to: '/manager/sales', icon: 'point_of_sale', label: 'Sales & Buyers' },
  { to: '/manager/inventory', icon: 'inventory_2', label: 'Inventory' },
  { to: '/manager/deductions', icon: 'money_off', label: 'Deductions' },
  { to: '/manager/reports', icon: 'description', label: 'Reports' },
  { to: '/manager/routes', icon: 'route', label: 'Routes' },
  { to: '/manager/audit-log', icon: 'security', label: 'Audit Log' },
]

const bottomItems = [
  { to: '/manager/settings', icon: 'settings', label: 'Settings' },
]

export default function Sidebar({ mobileOpen, onClose }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [entryOpen, setEntryOpen] = useState(false)

  useEffect(() => { onClose?.(); setEntryOpen(false) }, [pathname])

  const sidebarContent = (
    <aside className="w-64 h-full bg-primary flex flex-col py-6 px-4 overflow-y-auto">
      <div className="mb-10 px-2">
        <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Zao Manager</h1>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                isActive
                  ? 'bg-secondary-container text-on-secondary-container rounded-lg'
                  : 'text-on-primary/80 hover:text-on-primary hover:bg-primary-fixed-dim/10 rounded-lg'
              }`}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span className="font-body-md text-body-md">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {entryOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg overflow-hidden">
        </div>
      )}

      <div className="mt-auto pt-6 border-t border-on-primary/10 space-y-4">
        {bottomItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="flex items-center gap-3 px-4 py-2 text-on-primary/80 hover:text-on-primary transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            <span className="font-label-md text-label-md">{item.label}</span>
          </Link>
        ))}
      </div>
    </aside>
  )

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={onClose} />
      )}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 z-50">
        {sidebarContent}
      </div>
      <div className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:hidden ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {sidebarContent}
      </div>
    </>
  )
}

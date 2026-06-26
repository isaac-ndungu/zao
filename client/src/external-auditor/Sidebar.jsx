import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { to: '/external-auditor/financial-statements', icon: 'finance', label: 'Financial Statements' },
  { to: '/external-auditor/audit-trail', icon: 'security', label: 'Audit Trail' },
  { to: '/external-auditor/loan-portfolio', icon: 'account_balance_wallet', label: 'Loan Portfolio' },
]

export default function ExternalAuditorSidebar({ mobileOpen, onClose }) {
  const { pathname } = useLocation()

  const sidebarContent = (
    <aside className="w-64 h-full bg-primary flex flex-col py-6 px-4 overflow-y-auto">
      <div className="mb-10 px-2">
        <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Zao External Auditor</h1>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={onClose}
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

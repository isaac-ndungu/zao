import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'

const navItems = [
  { to: '/admin/dashboard', icon: 'dashboard', label: 'Dashboard' },
  { to: '/admin/cooperatives', icon: 'groups', label: 'Cooperatives' },
  { to: '/admin/ledger', icon: 'account_balance_wallet', label: 'Farmer Ledger' },
  { to: '/admin/receipts', icon: 'receipt_long', label: 'Produce Receipts' },
  { to: '/admin/inventory', icon: 'inventory_2', label: 'Inventory' },
  { to: '/admin/logistics', icon: 'local_shipping', label: 'Logistics' },
  { to: '/admin/financials', icon: 'payments', label: 'Financials' },
  { to: '/admin/loans', icon: 'account_balance', label: 'Loans' },
  { to: '/admin/farmer-payments', icon: 'payments', label: 'Farmer Payments' },
]

const systemItems = [
  { to: '/admin/users', icon: 'group', label: 'User Management' },
  { to: '/admin/audit', icon: 'history', label: 'Audit Trail' },
  { to: '/admin/otp-tokens', icon: 'pin', label: 'OTP Tokens' },
  { to: '/admin/trash', icon: 'delete_sweep', label: 'Trash' },
  { to: '/admin/health', icon: 'monitor_heart', label: 'System Health' },
]

const bottomItems = [
  { to: '/admin/settings', icon: 'settings', label: 'Settings' },
  { to: '/admin/support', icon: 'help', label: 'Support' },
]

const entryLinks = [
  { to: '/admin/users', label: 'Invite User', icon: 'person_add' },
  { to: '/admin/ledger', label: 'Register Farmer', icon: 'agriculture' },
  { to: '/admin/cooperatives', label: 'New Cooperative', icon: 'group_add' },
  { to: '/admin/loans', label: 'New Loan', icon: 'account_balance' },
  { to: '/admin/financials', label: 'New Payment Cycle', icon: 'payments' },
]

export default function Sidebar({ mobileOpen, onClose }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [entryOpen, setEntryOpen] = useState(false)

  useEffect(() => { onClose(); setEntryOpen(false) }, [pathname])

  const sidebarContent = (
    <aside className="w-64 h-full bg-primary flex flex-col py-6 px-4">
      <div className="mb-10 px-2">
        <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Zao Operations</h1>
        <p className="text-on-primary/60 font-label-md text-label-md">Central Rift Coop</p>
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

      <div className="px-2 pt-2 pb-1">
        <p className="text-[10px] uppercase font-bold text-on-primary/40 tracking-widest font-label-md">System</p>
      </div>
      <nav className="space-y-0.5 mb-2">
        {systemItems.map((item) => {
          const isActive = pathname.startsWith(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 px-4 py-2 transition-colors ${
                isActive
                  ? 'bg-secondary-container text-on-secondary-container rounded-lg'
                  : 'text-on-primary/60 hover:text-on-primary hover:bg-primary-fixed-dim/10 rounded-lg'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
              <span className="font-label-md text-label-md font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

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

        <div className="relative">
          <button
            onClick={() => setEntryOpen(!entryOpen)}
            onBlur={() => setTimeout(() => setEntryOpen(false), 200)}
            className="w-full bg-primary-fixed text-on-primary-fixed font-bold py-3 rounded-lg flex items-center justify-center gap-2 mt-4 hover:opacity-90 transition-opacity"
          >
            <span className="material-symbols-outlined">add</span>
            <span>New Entry</span>
          </button>
          {entryOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg overflow-hidden">
              {entryLinks.map((link) => (
                <button
                  key={link.to}
                  onMouseDown={() => { navigate(link.to, { state: { openModal: true } }); setEntryOpen(false) }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-body-md text-on-surface hover:bg-surface-container transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px] text-on-surface-variant">{link.icon}</span>
                  {link.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  )

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      {/* Desktop: fixed sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 z-50">
        {sidebarContent}
      </div>
      {/* Mobile: overlay sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </div>
    </>
  )
}

import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { to: '/admin/dashboard', icon: 'dashboard', label: 'Dashboard' },
  { to: '/admin/ledger', icon: 'account_balance_wallet', label: 'Farmer Ledger' },
  { to: '/admin/receipts', icon: 'receipt_long', label: 'Produce Receipts' },
  { to: '/admin/inventory', icon: 'inventory_2', label: 'Inventory' },
  { to: '/admin/logistics', icon: 'local_shipping', label: 'Logistics' },
  { to: '/admin/financials', icon: 'payments', label: 'Financials' },
]

const systemItems = [
  { to: '/admin/users', icon: 'group', label: 'User Management' },
  { to: '/admin/audit', icon: 'history', label: 'Audit Trail' },
  { to: '/admin/trash', icon: 'delete_sweep', label: 'Trash' },
  { to: '/admin/health', icon: 'monitor_heart', label: 'System Health' },
]

const bottomItems = [
  { to: '/admin/settings', icon: 'settings', label: 'Settings' },
  { to: '/admin/support', icon: 'help', label: 'Support' },
]

export default function Sidebar() {
  const { pathname } = useLocation()

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 bg-primary border-r border-outline-variant flex flex-col py-6 px-4 z-50">
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

        <button className="w-full bg-primary-fixed text-on-primary-fixed font-bold py-3 rounded-lg flex items-center justify-center gap-2 mt-4 hover:opacity-90 transition-opacity">
          <span className="material-symbols-outlined">add</span>
          <span>New Entry</span>
        </button>
      </div>
    </aside>
  )
}

import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'

const navItems = [
  { to: '/manager/dashboard', icon: 'dashboard', label: 'Dashboard' },
  { to: '/manager/farmers', icon: 'agriculture', label: 'Farmers' },
  { to: '/manager/users', icon: 'group', label: 'Staff' },
  { to: '/manager/deliveries', icon: 'local_shipping', label: 'Deliveries' },
  { to: '/manager/grading', icon: 'grading', label: 'Grading Queue' },
  { to: '/manager/disputes', icon: 'feedback', label: 'Disputes' },
  { to: '/manager/grade-prices', icon: 'monetization_on', label: 'Grade Prices' },
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
  { to: '/manager/profile', icon: 'person', label: 'Profile' },
  { to: '/manager/settings', icon: 'settings', label: 'Settings' },
]

function NavItem({ item, pathname, minimized, showTooltip, hideTooltip }) {
  const isActive = pathname.startsWith(item.to)
  return (
    <Link
      to={item.to}
      onMouseEnter={(e) => showTooltip(e, item.label)}
      onMouseLeave={hideTooltip}
      className={`flex items-center gap-3 px-4 py-3 transition-colors ${
        isActive
          ? 'bg-secondary-container text-on-secondary-container rounded-lg'
          : 'text-on-primary/80 hover:text-on-primary hover:bg-primary-fixed-dim/10 rounded-lg'
      }`}
      aria-current={isActive ? 'page' : undefined}
    >
      <span className="material-symbols-outlined" aria-hidden="true">{item.icon}</span>
      {!minimized && <span className="font-body-md text-body-md">{item.label}</span>}
    </Link>
  )
}

function BottomItem({ item, minimized, showTooltip, hideTooltip }) {
  return (
    <Link
      to={item.to}
      onMouseEnter={(e) => showTooltip(e, item.label)}
      onMouseLeave={hideTooltip}
      className="flex items-center gap-3 px-4 py-2 text-on-primary/80 hover:text-on-primary transition-colors"
    >
      <span className="material-symbols-outlined text-[20px]" aria-hidden="true">{item.icon}</span>
      {!minimized && <span className="font-label-md text-label-md">{item.label}</span>}
    </Link>
  )
}

export default function Sidebar({ mobileOpen, onClose, minimized }) {
  const { pathname } = useLocation()
  const [entryOpen, setEntryOpen] = useState(false)
  const [tooltip, setTooltip] = useState({ show: false, label: '', x: 0, y: 0 })

  useEffect(() => { onClose?.(); setEntryOpen(false) }, [pathname])

  const showTooltip = useCallback((e, label) => {
    if (!minimized) return
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltip({ show: true, label, x: rect.right + 8, y: rect.top + rect.height / 2 })
  }, [minimized])

  const hideTooltip = useCallback(() => {
    setTooltip({ show: false, label: '', x: 0, y: 0 })
  }, [])

  const sidebarContent = (
    <aside aria-label="Manager sidebar" className={`${minimized ? 'w-16 px-2' : 'w-64 px-4'} h-full bg-primary flex flex-col py-6 overflow-y-auto transition-all duration-300`}>
      <div className={`mb-10 ${minimized ? 'px-0 text-center' : 'px-2'}`}>
        {minimized ? (
          <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Z</h1>
        ) : (
          <h1 className="font-headline-lg text-headline-lg font-bold text-on-primary">Zao Manager</h1>
        )}
      </div>

      <nav aria-label="Main navigation" className="flex-1 space-y-1">
        {navItems.map((item) => (
          <NavItem key={item.to} item={item} pathname={pathname} minimized={minimized} showTooltip={showTooltip} hideTooltip={hideTooltip} />
        ))}
      </nav>

      <div className={`mt-auto pt-6 border-t border-on-primary/10 ${minimized ? 'space-y-2' : 'space-y-4'}`}>
        {bottomItems.map((item) => (
          <BottomItem key={item.to} item={item} minimized={minimized} showTooltip={showTooltip} hideTooltip={hideTooltip} />
        ))}
      </div>
    </aside>
  )

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden cursor-pointer" onClick={onClose} aria-hidden="true" />
      )}
      <div className={`hidden lg:fixed lg:inset-y-0 lg:flex ${minimized ? 'lg:w-16' : 'lg:w-64'} z-50 transition-all duration-300`}>
        {sidebarContent}
      </div>
      <div className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:hidden ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {sidebarContent}
      </div>
      {minimized && tooltip.show && (
        <div
          className="fixed px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap pointer-events-none z-[999] shadow-lg"
          style={{ left: tooltip.x, top: tooltip.y, transform: 'translateY(-50%)' }}
        >
          {tooltip.label}
        </div>
      )}
    </>
  )
}

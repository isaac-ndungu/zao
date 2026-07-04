import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAdminAuth } from '../../hooks/useAdminAuth'
import PeriodPicker from './PeriodPicker'
import NotificationBell from '../../../shared/components/NotificationBell'
import ProfileDropdown from '../../../shared/components/ProfileDropdown'
import SearchBar from '../../../shared/components/SearchBar'
import LegalHistoryDropdown from './LegalHistoryDropdown'

const appBarTabs = [
  { label: 'Analytics', path: '/admin/dashboard' },
  { label: 'Reports', path: '/admin/financials' },
  { label: 'Audit Trail', path: '/admin/audit' },
]

export default function AppBar({ onMenuClick, minimized, onToggle }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAdminAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  return (
    <header className={`fixed top-0 right-0 ${minimized ? 'lg:left-16' : 'lg:left-64'} h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-4 lg:px-6 z-30 transition-all duration-300`}>
      <div className="flex items-center gap-3 lg:gap-8 flex-1 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 text-on-surface-variant hover:bg-surface-container-high rounded-lg transition-colors"
          aria-label="Toggle menu"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>

        <button
          onClick={onToggle}
          className="hidden lg:flex p-2 text-on-surface-variant hover:bg-surface-container-high rounded-lg transition-colors"
          aria-label={minimized ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <span className="material-symbols-outlined">{minimized ? 'menu' : 'menu_open'}</span>
        </button>

        <SearchBar role="admin" placeholder="Search operations, records, or farmers..." />

        {['/admin/dashboard', '/admin/ledger', '/admin/financials', '/admin/inventory', '/admin/logistics', '/admin/analytics/seasonal', '/admin/analytics/retention'].some(p => pathname.startsWith(p)) && (
          <div className="hidden md:block flex-shrink-0">
            <PeriodPicker />
          </div>
        )}

        <nav className="hidden xl:flex gap-6 ml-auto">
          {appBarTabs.map((tab) => {
            const isActive = pathname.startsWith(tab.path)
            return (
              <button
                key={tab.label}
                onClick={() => navigate(tab.path)}
                className={`font-label-md text-label-md transition-colors whitespace-nowrap ${isActive
                  ? 'text-primary font-bold border-b-2 border-primary pb-1'
                  : 'text-on-surface-variant font-medium hover:text-primary'
                  }`}
              >
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="flex items-center gap-2 lg:gap-4 flex-shrink-0">
        <NotificationBell />

        <LegalHistoryDropdown />

        <div className="relative flex items-center gap-3 pl-2 lg:pl-4 border-l border-outline-variant">
          <div className="text-right hidden xl:block">
            <p className="font-label-md font-bold text-on-surface leading-tight truncate max-w-[120px]">
              {user ? `${user.first_name} ${user.last_name}` : 'Loading...'}
            </p>
            <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">
              Super Admin
            </p>
          </div>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="w-9 h-9 lg:w-10 lg:h-10 rounded-full bg-primary-fixed flex items-center justify-center border border-outline-variant text-primary font-bold text-sm overflow-hidden flex-shrink-0 hover:ring-2 hover:ring-primary transition-all cursor-pointer"
            aria-label="Open profile menu"
          >
            {user?.avatar ? (
              <img src={user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              initials
            )}
          </button>
          {dropdownOpen && (
            <ProfileDropdown
              profilePath="/admin/profile"
              roleLabel="Super Admin"
              onClose={() => setDropdownOpen(false)}
            />
          )}
        </div>
      </div>
    </header>
  )
}

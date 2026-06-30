import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../shared/hooks/useAuth'
import { useApi } from '../admin/hooks/useApi'
import ProfileDropdown from '../shared/components/ProfileDropdown'

export default function AuditorAppBar({ onMenuClick, minimized, onToggle }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: coop } = useApi('/api/cooperatives/me/')
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const initials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : '??'

  const coopName = coop?.name || ''

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

        <form
          onSubmit={(e) => {
            e.preventDefault()
            const fd = new FormData(e.target)
            const q = fd.get('search')
            if (q?.trim()) navigate(`/auditor/audit-log?search=${encodeURIComponent(q.trim())}`)
          }}
          className="relative hidden sm:block sm:w-60 lg:w-72 flex-shrink-0"
        >
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
            search
          </span>
          <input
            name="search"
            className="w-full bg-surface-container border-none rounded-full py-2 pl-10 pr-4 text-body-md focus:ring-1 focus:ring-primary"
            placeholder="Search audit log..."
          />
        </form>
      </div>

      <div className="flex items-center gap-2 lg:gap-4 flex-shrink-0">
        {coopName && (
          <span className="hidden md:block text-label-md text-on-surface-variant font-medium mr-2">
            {coopName}
          </span>
        )}

        <div className="relative flex items-center gap-3 pl-2 lg:pl-4 border-l border-outline-variant">
          <div className="text-right hidden xl:block">
            <p className="font-label-md font-bold text-on-surface leading-tight truncate max-w-[120px]">
              {user ? `${user.first_name} ${user.last_name}` : 'Loading...'}
            </p>
            <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">
              Internal Auditor
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
              profilePath="/auditor/profile"
              roleLabel="Internal Auditor"
              onClose={() => setDropdownOpen(false)}
            />
          )}
        </div>
      </div>
    </header>
  )
}

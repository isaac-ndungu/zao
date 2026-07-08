import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { createPortal } from 'react-dom'
import { ToastProvider } from './ToastProvider'
import OfflineBanner from './OfflineBanner'
import ChatWidget from './ChatWidget'
import FloatingAccessibilityWidget, { A11yProvider } from './FloatingAccessibilityWidget'
import SkipLink from './SkipLink'

export default function DashboardLayout({ sidebar, header, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarMinimized, setSidebarMinimized] = useState(true)

  return (
    <A11yProvider>
      <ToastProvider>
        <SkipLink />
        {createPortal(<FloatingAccessibilityWidget mode="staff" />, document.body)}
        <div className="flex min-h-screen bg-background">
          {sidebar && (
            <>
              {typeof sidebar === 'function'
                ? sidebar({
                    mobileOpen: sidebarOpen,
                    onClose: () => setSidebarOpen(false),
                    minimized: sidebarMinimized,
                    onToggle: () => setSidebarMinimized(v => !v),
                  })
                : sidebar}
            </>
          )}
          <div className={sidebar ? `flex-1 ${sidebarMinimized ? 'lg:ml-16' : 'lg:ml-64'}` : 'flex-1'}>
            {header && (
              typeof header === 'function'
                ? header({
                    onMenuClick: () => setSidebarOpen(!sidebarOpen),
                    minimized: sidebarMinimized,
                    onToggle: () => setSidebarMinimized(v => !v),
                  })
                : header
            )}
            <OfflineBanner />
            <main id="main-content" className={`${header ? 'mt-16' : ''} p-container-margin min-h-[calc(100vh-4rem)] max-w-[1600px] mx-auto w-full`}>
              {children || <Outlet />}
            </main>
            <ChatWidget />
          </div>
        </div>
      </ToastProvider>
    </A11yProvider>
  )
}

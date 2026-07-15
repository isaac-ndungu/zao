import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { createPortal } from 'react-dom'
import { ToastProvider } from './ToastProvider'
import OfflineBanner from './OfflineBanner'
import FloatingAccessibilityWidget from './FloatingAccessibilityWidget'
import SkipLink from './SkipLink'

const ChatWidget = React.lazy(() => import('./ChatWidget'))

export default function DashboardLayout({ sidebar, header, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarMinimized, setSidebarMinimized] = useState(true)
  const [chatOpen, setChatOpen] = useState(false)

  return (
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
          {chatOpen && (
            <React.Suspense fallback={null}>
              <ChatWidget onClose={() => setChatOpen(false)} />
            </React.Suspense>
          )}
          {!chatOpen && (
            <button
              onClick={() => setChatOpen(true)}
              className="fixed bottom-6 right-6 w-11 h-11 bg-primary text-on-primary rounded-full shadow-lg flex items-center justify-center z-50 hover:bg-primary-container hover:text-primary transition-colors"
              aria-label="Open chat"
            >
              <span className="material-symbols-outlined text-xl" aria-hidden="true">chat</span>
            </button>
          )}
        </div>
      </div>
    </ToastProvider>
  )
}

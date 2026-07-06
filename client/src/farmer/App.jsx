import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { FarmerAuthProvider } from './context/FarmerAuthContext'
import { ToastProvider } from './components/Toast'
import BottomNav from './components/BottomNav'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Deliveries from './pages/Deliveries'
import Payments from './pages/Payments'
import Grades from './pages/Grades'
import Loans from './pages/Loans'
import Profile from './pages/Profile'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import FloatingAccessibilityWidget, { A11yProvider } from '../shared/components/FloatingAccessibilityWidget'

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('zao_farmer_token')
  if (!token) return <Navigate to="/farmer/login" replace />
  return children
}

function FarmerLayout({ children }) {
  return (
    <div className="min-h-screen max-w-lg mx-auto bg-surface relative pb-20">
      <div className="px-4 pt-4">
        {children}
      </div>
    </div>
  )
}

function TabRoute({ children }) {
  return (
    <ProtectedRoute>
      <FarmerLayout>
        {children}
        <BottomNav />
        <FloatingAccessibilityWidget mode="farmer" />
      </FarmerLayout>
    </ProtectedRoute>
  )
}

function LanguageResetTrigger() {
  const [, setLangKey] = useState(0)
  useEffect(() => {
    const handler = () => setLangKey(k => k + 1)
    window.addEventListener('zao-i18n-change', handler)
    return () => window.removeEventListener('zao-i18n-change', handler)
  }, [])
  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <A11yProvider>
        <LanguageResetTrigger />
        <ToastProvider>
          <FarmerAuthProvider>
            <Routes>
              <Route path="/farmer/login" element={<Login />} />
              <Route path="/farmer/dashboard" element={<TabRoute><Dashboard /></TabRoute>} />
              <Route path="/farmer/deliveries" element={<TabRoute><Deliveries /></TabRoute>} />
              <Route path="/farmer/payments" element={<TabRoute><Payments /></TabRoute>} />
              <Route path="/farmer/grades" element={<TabRoute><Grades /></TabRoute>} />
              <Route path="/farmer/profile" element={<TabRoute><Profile /></TabRoute>} />
              <Route path="/farmer/loans" element={<ProtectedRoute><FarmerLayout><Loans /></FarmerLayout></ProtectedRoute>} />
              <Route path="/farmer/chat" element={<ProtectedRoute><FarmerLayout><Chat /></FarmerLayout></ProtectedRoute>} />
              <Route path="/farmer/settings" element={<ProtectedRoute><FarmerLayout><Settings /></FarmerLayout></ProtectedRoute>} />
              <Route path="/farmer/*" element={<Navigate to="/farmer/dashboard" replace />} />
            </Routes>
          </FarmerAuthProvider>
        </ToastProvider>
      </A11yProvider>
    </BrowserRouter>
  )
}

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Solutions from './pages/Solutions'
import ForFarmers from './pages/ForFarmers'
import About from './pages/About'
import { AdminAuthProvider } from './admin/contexts/AdminAuthContext'
import AdminGuard from './admin/components/common/AdminGuard'
import Login from './admin/pages/Login'

function DashboardPlaceholder() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#eaffea]">
      <p className="text-headline-lg text-primary">Dashboard — Phase 2</p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AdminAuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/solutions" element={<Solutions />} />
          <Route path="/farmers" element={<ForFarmers />} />
          <Route path="/about" element={<About />} />
          <Route path="/admin/login" element={<Login />} />
          <Route path="/admin" element={<AdminGuard><Navigate to="/admin/dashboard" replace /></AdminGuard>} />
          <Route path="/admin/dashboard" element={<AdminGuard><DashboardPlaceholder /></AdminGuard>} />
        </Routes>
      </AdminAuthProvider>
    </BrowserRouter>
  )
}

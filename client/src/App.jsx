import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Solutions from './pages/Solutions'
import ForFarmers from './pages/ForFarmers'
import About from './pages/About'
import { AdminAuthProvider } from './admin/contexts/AdminAuthContext'
import AdminGuard from './admin/components/common/AdminGuard'
import AdminLayout from './admin/layouts/AdminLayout'
import Login from './admin/pages/Login'

function DashboardPlaceholder() {
  return (
    <div>
      <p className="text-headline-lg text-primary">Dashboard — Phase 3</p>
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
          <Route path="/admin" element={<AdminGuard><AdminLayout /></AdminGuard>}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPlaceholder />} />
          </Route>
        </Routes>
      </AdminAuthProvider>
    </BrowserRouter>
  )
}

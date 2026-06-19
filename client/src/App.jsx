import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Solutions from './pages/Solutions'
import ForFarmers from './pages/ForFarmers'
import About from './pages/About'
import { AdminAuthProvider } from './admin/contexts/AdminAuthContext'
import AdminGuard from './admin/components/common/AdminGuard'
import AdminLayout from './admin/layouts/AdminLayout'
import Login from './admin/pages/Login'
import Dashboard from './admin/pages/Dashboard'
import FarmerLedger from './admin/pages/FarmerLedger'
import ProduceReceipts from './admin/pages/ProduceReceipts'
import Inventory from './admin/pages/Inventory'
import Logistics from './admin/pages/Logistics'
import Financials from './admin/pages/Financials'
import Settings from './admin/pages/Settings'
import Support from './admin/pages/Support'
import UserManagement from './admin/pages/UserManagement'
import AuditTrail from './admin/pages/AuditTrail'
import TrashManagement from './admin/pages/TrashManagement'
import HealthMonitor from './admin/pages/HealthMonitor'
import Cooperatives from './admin/pages/Cooperatives'
import Loans from './admin/pages/Loans'
import FarmerPayments from './admin/pages/FarmerPayments'

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
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="ledger" element={<FarmerLedger />} />
            <Route path="receipts" element={<ProduceReceipts />} />
            <Route path="inventory" element={<Inventory />} />
            <Route path="logistics" element={<Logistics />} />
            <Route path="financials" element={<Financials />} />
            <Route path="settings" element={<Settings />} />
            <Route path="support" element={<Support />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="audit" element={<AuditTrail />} />
            <Route path="trash" element={<TrashManagement />} />
            <Route path="health" element={<HealthMonitor />} />
            <Route path="cooperatives" element={<Cooperatives />} />
            <Route path="loans" element={<Loans />} />
            <Route path="farmer-payments" element={<FarmerPayments />} />
          </Route>
        </Routes>
      </AdminAuthProvider>
    </BrowserRouter>
  )
}

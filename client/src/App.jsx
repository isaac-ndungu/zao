import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AdminAuthProvider } from './admin/contexts/AdminAuthContext'
import AdminGuard from './admin/components/common/AdminGuard'
import AdminLayout from './admin/layouts/AdminLayout'
import RoleGuard from './shared/components/RoleGuard'
import DashboardLayout from './shared/components/DashboardLayout'
import LegalAcceptanceGate from './shared/components/LegalAcceptanceGate'

// Public pages
const Home = lazy(() => import('./pages/Home'))
const Solutions = lazy(() => import('./pages/Solutions'))
const ForFarmers = lazy(() => import('./pages/ForFarmers'))
const About = lazy(() => import('./pages/About'))

// Auth pages
const Login = lazy(() => import('./admin/pages/Login'))
const FarmerLogin = lazy(() => import('./farmer/pages/Login'))

// Admin pages
const AdminDashboard = lazy(() => import('./admin/pages/Dashboard'))
const FarmerLedger = lazy(() => import('./admin/pages/FarmerLedger'))
const ProduceReceipts = lazy(() => import('./admin/pages/ProduceReceipts'))
const AdminInventory = lazy(() => import('./admin/pages/Inventory'))
const Logistics = lazy(() => import('./admin/pages/Logistics'))
const Financials = lazy(() => import('./admin/pages/Financials'))
const Settings = lazy(() => import('./admin/pages/Settings'))
const Support = lazy(() => import('./admin/pages/Support'))
const UserManagement = lazy(() => import('./admin/pages/UserManagement'))
const AuditTrail = lazy(() => import('./admin/pages/AuditTrail'))
const TrashManagement = lazy(() => import('./admin/pages/TrashManagement'))
const HealthMonitor = lazy(() => import('./admin/pages/HealthMonitor'))
const Cooperatives = lazy(() => import('./admin/pages/Cooperatives'))
const Loans = lazy(() => import('./admin/pages/Loans'))
const FarmerPayments = lazy(() => import('./admin/pages/FarmerPayments'))
const OTPTokens = lazy(() => import('./admin/pages/OTPTokens'))
const SeasonalPatterns = lazy(() => import('./admin/pages/SeasonalPatterns'))
const FarmerRetention = lazy(() => import('./admin/pages/FarmerRetention'))
const AdminNotFound = lazy(() => import('./admin/pages/NotFound'))

// Farmer pages 
const FarmerDashboard = lazy(() => import('./farmer/pages/Dashboard'))

// Manager pages
const ManagerLayout = lazy(() => import('./manager/ManagerLayout'))
const ManagerDashboard = lazy(() => import('./manager/pages/Dashboard'))
const Farmers = lazy(() => import('./manager/pages/Farmers'))
const Deliveries = lazy(() => import('./manager/pages/Deliveries'))
const GradingQueue = lazy(() => import('./manager/pages/GradingQueue'))
const Cycles = lazy(() => import('./manager/pages/Cycles'))
const ManagerDisbursements = lazy(() => import('./manager/pages/Disbursements'))
const ManagerLoans = lazy(() => import('./manager/pages/Loans'))
const SalesBuyers = lazy(() => import('./manager/pages/SalesBuyers'))
const ManagerInventory = lazy(() => import('./manager/pages/Inventory'))
const ManagerDeductions = lazy(() => import('./manager/pages/Deductions'))
const ManagerReports = lazy(() => import('./manager/pages/Reports'))
const ManagerRoutes = lazy(() => import('./manager/pages/Routes'))
const ManagerSettings = lazy(() => import('./manager/pages/Settings'))

// Grader pages
const GraderLayout = lazy(() => import('./grader/GraderLayout'))
const GraderDashboard = lazy(() => import('./grader/pages/Dashboard'))
const Grade = lazy(() => import('./grader/pages/Grade'))
const MyGrades = lazy(() => import('./grader/pages/MyGrades'))
const GraderSync = lazy(() => import('./grader/pages/Sync'))
const GraderSettings = lazy(() => import('./grader/pages/Settings'))

function SuspenseFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}

function PlaceholderPage({ title }) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <h1 className="font-headline-lg text-headline-lg text-primary mb-4">{title}</h1>
        <p className="text-body-md text-on-surface-variant">This dashboard is coming soon.</p>
      </div>
    </div>
  )
}

function RolePlaceholder({ roles }) {
  return (
    <RoleGuard roles={roles}>
      <LegalAcceptanceGate>
        <DashboardLayout>
          <PlaceholderPage title={`${roles[0]?.charAt(0).toUpperCase() + roles[0]?.slice(1)} Dashboard`} />
        </DashboardLayout>
      </LegalAcceptanceGate>
    </RoleGuard>
  )
}

function AdminRoutes() {
  return (
    <AdminGuard>
      <AdminLayout />
    </AdminGuard>
  )
}

function FarmerRoutes() {
  return (
    <RoleGuard roles={['farmer']}>
      <LegalAcceptanceGate>
        <DashboardLayout />
      </LegalAcceptanceGate>
    </RoleGuard>
  )
}

function SuspenseWrapper({ children }) {
  return <Suspense fallback={<SuspenseFallback />}>{children}</Suspense>
}

export default function App() {
  return (
    <BrowserRouter>
      <AdminAuthProvider>
        <Routes>
          {/* Public marketing routes */}
          <Route path="/" element={<SuspenseWrapper><Home /></SuspenseWrapper>} />
          <Route path="/solutions" element={<SuspenseWrapper><Solutions /></SuspenseWrapper>} />
          <Route path="/farmers" element={<SuspenseWrapper><ForFarmers /></SuspenseWrapper>} />
          <Route path="/about" element={<SuspenseWrapper><About /></SuspenseWrapper>} />

          {/* Login pages */}
          <Route path="/admin/login" element={<SuspenseWrapper><Login /></SuspenseWrapper>} />
          <Route path="/farmer/login" element={<SuspenseWrapper><FarmerLogin /></SuspenseWrapper>} />

          {/* Super-admin / Admin routes */}
          <Route path="/admin" element={<AdminRoutes />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><AdminDashboard /></SuspenseWrapper>} />
            <Route path="ledger" element={<SuspenseWrapper><FarmerLedger /></SuspenseWrapper>} />
            <Route path="receipts" element={<SuspenseWrapper><ProduceReceipts /></SuspenseWrapper>} />
            <Route path="inventory" element={<SuspenseWrapper><AdminInventory /></SuspenseWrapper>} />
            <Route path="logistics" element={<SuspenseWrapper><Logistics /></SuspenseWrapper>} />
            <Route path="financials" element={<SuspenseWrapper><Financials /></SuspenseWrapper>} />
            <Route path="settings" element={<SuspenseWrapper><Settings /></SuspenseWrapper>} />
            <Route path="support" element={<SuspenseWrapper><Support /></SuspenseWrapper>} />
            <Route path="users" element={<SuspenseWrapper><UserManagement /></SuspenseWrapper>} />
            <Route path="audit" element={<SuspenseWrapper><AuditTrail /></SuspenseWrapper>} />
            <Route path="trash" element={<SuspenseWrapper><TrashManagement /></SuspenseWrapper>} />
            <Route path="health" element={<SuspenseWrapper><HealthMonitor /></SuspenseWrapper>} />
            <Route path="cooperatives" element={<SuspenseWrapper><Cooperatives /></SuspenseWrapper>} />
            <Route path="loans" element={<SuspenseWrapper><Loans /></SuspenseWrapper>} />
            <Route path="farmer-payments" element={<SuspenseWrapper><FarmerPayments /></SuspenseWrapper>} />
            <Route path="otp-tokens" element={<SuspenseWrapper><OTPTokens /></SuspenseWrapper>} />
            <Route path="analytics/seasonal" element={<SuspenseWrapper><SeasonalPatterns /></SuspenseWrapper>} />
            <Route path="analytics/retention" element={<SuspenseWrapper><FarmerRetention /></SuspenseWrapper>} />
            <Route path="*" element={<SuspenseWrapper><AdminNotFound /></SuspenseWrapper>} />
          </Route>

          {/* Manager dashboard */}
          <Route path="/manager" element={
            <RoleGuard roles={['manager']}>
              <LegalAcceptanceGate>
                <ManagerLayout />
              </LegalAcceptanceGate>
            </RoleGuard>
          }>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><ManagerDashboard /></SuspenseWrapper>} />
            <Route path="farmers" element={<SuspenseWrapper><Farmers /></SuspenseWrapper>} />
            <Route path="deliveries" element={<SuspenseWrapper><Deliveries /></SuspenseWrapper>} />
            <Route path="grading" element={<SuspenseWrapper><GradingQueue /></SuspenseWrapper>} />
            <Route path="cycles" element={<SuspenseWrapper><Cycles /></SuspenseWrapper>} />
            <Route path="disbursements" element={<SuspenseWrapper><ManagerDisbursements /></SuspenseWrapper>} />
            <Route path="loans" element={<SuspenseWrapper><ManagerLoans /></SuspenseWrapper>} />
            <Route path="sales" element={<SuspenseWrapper><SalesBuyers /></SuspenseWrapper>} />
            <Route path="inventory" element={<SuspenseWrapper><ManagerInventory /></SuspenseWrapper>} />
            <Route path="deductions" element={<SuspenseWrapper><ManagerDeductions /></SuspenseWrapper>} />
            <Route path="reports" element={<SuspenseWrapper><ManagerReports /></SuspenseWrapper>} />
            <Route path="routes" element={<SuspenseWrapper><ManagerRoutes /></SuspenseWrapper>} />
            <Route path="settings" element={<SuspenseWrapper><ManagerSettings /></SuspenseWrapper>} />
          </Route>

          {/* Grader dashboard */}
          <Route path="/grader" element={
            <RoleGuard roles={['grader']}>
              <LegalAcceptanceGate>
                <GraderLayout />
              </LegalAcceptanceGate>
            </RoleGuard>
          }>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><GraderDashboard /></SuspenseWrapper>} />
            <Route path="grade" element={<SuspenseWrapper><Grade /></SuspenseWrapper>} />
            <Route path="my-grades" element={<SuspenseWrapper><MyGrades /></SuspenseWrapper>} />
            <Route path="sync" element={<SuspenseWrapper><GraderSync /></SuspenseWrapper>} />
            <Route path="settings" element={<SuspenseWrapper><GraderSettings /></SuspenseWrapper>} />
          </Route>

          {/* Accountant dashboard  */}
          <Route path="/accountant/*" element={<RolePlaceholder roles={['accountant']} />} />

          {/* Internal auditor dashboard */}
          <Route path="/auditor/*" element={<RolePlaceholder roles={['auditor']} />} />

          {/* External auditor dashboard */}
          <Route path="/external-auditor/*" element={<RolePlaceholder roles={['external_auditor']} />} />

          {/* Farmer dashboard  */}
          <Route path="/farmer" element={<FarmerRoutes />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><FarmerDashboard /></SuspenseWrapper>} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AdminAuthProvider>
    </BrowserRouter>
  )
}

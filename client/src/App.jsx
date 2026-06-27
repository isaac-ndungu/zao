import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AdminAuthProvider } from './admin/contexts/AdminAuthContext'
import AdminGuard from './admin/components/common/AdminGuard'
import AdminLayout from './admin/layouts/AdminLayout'
import RoleGuard from './shared/components/RoleGuard'
import DashboardLayout from './shared/components/DashboardLayout'
import LegalAcceptanceGate from './shared/components/LegalAcceptanceGate'
import ErrorBoundary from './shared/components/ErrorBoundary'
import { FarmerAuthProvider } from './farmer/context/FarmerAuthContext'
import { ToastProvider } from './farmer/components/Toast'
import BottomNav from './farmer/components/BottomNav'

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
const AdminFarmerPayments = lazy(() => import('./admin/pages/FarmerPayments'))
const OTPTokens = lazy(() => import('./admin/pages/OTPTokens'))
const SeasonalPatterns = lazy(() => import('./admin/pages/SeasonalPatterns'))
const FarmerRetention = lazy(() => import('./admin/pages/FarmerRetention'))
const AdminNotFound = lazy(() => import('./admin/pages/NotFound'))

// Farmer pages 
const FarmerDashboard = lazy(() => import('./farmer/pages/Dashboard'))
const FarmerDeliveries = lazy(() => import('./farmer/pages/Deliveries'))
const FarmerPayments = lazy(() => import('./farmer/pages/Payments'))
const FarmerGrades = lazy(() => import('./farmer/pages/Grades'))
const FarmerLoans = lazy(() => import('./farmer/pages/Loans'))
const FarmerProfile = lazy(() => import('./farmer/pages/Profile'))
const FarmerChat = lazy(() => import('./farmer/pages/Chat'))
const FarmerSettings = lazy(() => import('./farmer/pages/Settings'))

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

// Accountant pages
const AccountantLayout = lazy(() => import('./accountant/AccountantLayout'))
const AccountantDashboard = lazy(() => import('./accountant/pages/Dashboard'))
const AccountantCycles = lazy(() => import('./accountant/pages/Cycles'))
const AccountantDisbursements = lazy(() => import('./accountant/pages/Disbursements'))
const AccountantLoans = lazy(() => import('./accountant/pages/Loans'))
const AccountantDeductions = lazy(() => import('./accountant/pages/Deductions'))
const AccountantReports = lazy(() => import('./accountant/pages/Reports'))
const AccountantSettings = lazy(() => import('./accountant/pages/Settings'))

// Auditor pages
const AuditorLayout = lazy(() => import('./auditor/AuditorLayout'))
const AuditorDashboard = lazy(() => import('./auditor/pages/Dashboard'))
const AuditorAuditLog = lazy(() => import('./auditor/pages/AuditLog'))
const AuditorFinancial = lazy(() => import('./auditor/pages/Financial'))
const AuditorProduction = lazy(() => import('./auditor/pages/Production'))
const AuditorLoans = lazy(() => import('./auditor/pages/Loans'))
const AuditorReports = lazy(() => import('./auditor/pages/Reports'))
const AuditorSettings = lazy(() => import('./auditor/pages/Settings'))

// External auditor pages
const ExternalAuditorLayout = lazy(() => import('./external-auditor/ExternalAuditorLayout'))
const ExternalFinancialStatements = lazy(() => import('./external-auditor/pages/FinancialStatements'))
const ExternalAuditTrail = lazy(() => import('./external-auditor/pages/AuditTrail'))
const ExternalLoanPortfolio = lazy(() => import('./external-auditor/pages/LoanPortfolio'))

function SuspenseFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )
}

function AdminRoutes() {
  return (
    <AdminGuard>
      <ErrorBoundary>
        <AdminLayout />
      </ErrorBoundary>
    </AdminGuard>
  )
}

// Farmer mobile layout with bottom navigation
function FarmerLayoutWithNav() {
  return (
    <div className="min-h-screen max-w-lg mx-auto bg-surface relative pb-20">
      <div className="px-4 pt-4">
        <Outlet />   {/* Renders the matched child route (dashboard, deliveries, etc.) */}
      </div>
      <BottomNav />
    </div>
  )
}

// Authenticated farmer layout with role guard, legal gate, etc.
function FarmerAuthenticatedLayout() {
  return (
    <RoleGuard roles={['farmer']}>
      <LegalAcceptanceGate>
        <ErrorBoundary>
          <FarmerLayoutWithNav />
        </ErrorBoundary>
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
            <Route path="farmer-payments" element={<SuspenseWrapper><AdminFarmerPayments /></SuspenseWrapper>} />
            <Route path="otp-tokens" element={<SuspenseWrapper><OTPTokens /></SuspenseWrapper>} />
            <Route path="analytics/seasonal" element={<SuspenseWrapper><SeasonalPatterns /></SuspenseWrapper>} />
            <Route path="analytics/retention" element={<SuspenseWrapper><FarmerRetention /></SuspenseWrapper>} />
            <Route path="*" element={<SuspenseWrapper><AdminNotFound /></SuspenseWrapper>} />
          </Route>

          {/* Manager dashboard */}
          <Route path="/manager" element={
            <RoleGuard roles={['manager']}>
              <LegalAcceptanceGate>
                <ErrorBoundary>
                  <ManagerLayout />
                </ErrorBoundary>
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
                <ErrorBoundary>
                  <GraderLayout />
                </ErrorBoundary>
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

          {/* Accountant dashboard */}
          <Route path="/accountant" element={
            <RoleGuard roles={['accountant']}>
              <LegalAcceptanceGate>
                <ErrorBoundary>
                  <AccountantLayout />
                </ErrorBoundary>
              </LegalAcceptanceGate>
            </RoleGuard>
          }>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><AccountantDashboard /></SuspenseWrapper>} />
            <Route path="cycles" element={<SuspenseWrapper><AccountantCycles /></SuspenseWrapper>} />
            <Route path="disbursements" element={<SuspenseWrapper><AccountantDisbursements /></SuspenseWrapper>} />
            <Route path="loans" element={<SuspenseWrapper><AccountantLoans /></SuspenseWrapper>} />
            <Route path="deductions" element={<SuspenseWrapper><AccountantDeductions /></SuspenseWrapper>} />
            <Route path="reports" element={<SuspenseWrapper><AccountantReports /></SuspenseWrapper>} />
            <Route path="settings" element={<SuspenseWrapper><AccountantSettings /></SuspenseWrapper>} />
          </Route>

          {/* Internal auditor dashboard */}
          <Route path="/auditor" element={
            <RoleGuard roles={['auditor']}>
              <LegalAcceptanceGate>
                <ErrorBoundary>
                  <AuditorLayout />
                </ErrorBoundary>
              </LegalAcceptanceGate>
            </RoleGuard>
          }>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<SuspenseWrapper><AuditorDashboard /></SuspenseWrapper>} />
            <Route path="audit-log" element={<SuspenseWrapper><AuditorAuditLog /></SuspenseWrapper>} />
            <Route path="financial" element={<SuspenseWrapper><AuditorFinancial /></SuspenseWrapper>} />
            <Route path="production" element={<SuspenseWrapper><AuditorProduction /></SuspenseWrapper>} />
            <Route path="loans" element={<SuspenseWrapper><AuditorLoans /></SuspenseWrapper>} />
            <Route path="reports" element={<SuspenseWrapper><AuditorReports /></SuspenseWrapper>} />
            <Route path="settings" element={<SuspenseWrapper><AuditorSettings /></SuspenseWrapper>} />
          </Route>

          {/* External auditor dashboard */}
          <Route path="/external-auditor" element={
            <RoleGuard roles={['external_auditor']}>
              <LegalAcceptanceGate>
                <ErrorBoundary>
                  <ExternalAuditorLayout />
                </ErrorBoundary>
              </LegalAcceptanceGate>
            </RoleGuard>
          }>
            <Route index element={<Navigate to="financial-statements" replace />} />
            <Route path="financial-statements" element={<SuspenseWrapper><ExternalFinancialStatements /></SuspenseWrapper>} />
            <Route path="audit-trail" element={<SuspenseWrapper><ExternalAuditTrail /></SuspenseWrapper>} />
            <Route path="loan-portfolio" element={<SuspenseWrapper><ExternalLoanPortfolio /></SuspenseWrapper>} />
          </Route>

          {/* Farmer auth */}
          <Route element={<FarmerAuthProvider><Outlet /></FarmerAuthProvider>}>
            <Route element={<ToastProvider><Outlet /></ToastProvider>}>
              <Route path="/farmer/login" element={<SuspenseWrapper><FarmerLogin /></SuspenseWrapper>} />
              <Route path="/farmer" element={<FarmerAuthenticatedLayout />}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<SuspenseWrapper><FarmerDashboard /></SuspenseWrapper>} />
                <Route path="deliveries" element={<SuspenseWrapper><FarmerDeliveries /></SuspenseWrapper>} />
                <Route path="payments" element={<SuspenseWrapper><FarmerPayments /></SuspenseWrapper>} />
                <Route path="grades" element={<SuspenseWrapper><FarmerGrades /></SuspenseWrapper>} />
                <Route path="loans" element={<SuspenseWrapper><FarmerLoans /></SuspenseWrapper>} />
                <Route path="profile" element={<SuspenseWrapper><FarmerProfile /></SuspenseWrapper>} />
                <Route path="chat" element={<SuspenseWrapper><FarmerChat /></SuspenseWrapper>} />
                <Route path="settings" element={<SuspenseWrapper><FarmerSettings /></SuspenseWrapper>} />
              </Route>
            </Route>
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AdminAuthProvider>
    </BrowserRouter>
  )
}

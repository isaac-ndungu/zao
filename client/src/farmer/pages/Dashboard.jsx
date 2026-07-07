import { useNavigate } from 'react-router-dom'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import NotificationBell from '../components/NotificationBell'
import { CardSkeleton, KpiSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'

function formatKes(n) {
  if (!n || n === 0) return 'KES 0'
  if (n >= 1_000_000) return `KES ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `KES ${(n / 1_000).toFixed(1)}K`
  return `KES ${Number(n).toLocaleString()}`
}

// Helper to check if a delivery is from today
function isToday(dateStr) {
  if (!dateStr) return false
  const today = new Date()
  const d = new Date(dateStr)
  return d.toDateString() === today.toDateString()
}

export default function FarmerDashboard() {
  const navigate = useNavigate()
  const { user } = useFarmerAuth()
  const { showToast } = useToast()
  const { data: profile, loading: profileLoading, error: profileError, refetch: refetchProfile } = useFarmerApi('/api/farmers/me/')
  const { data: history, loading: historyLoading, error: historyError } = useFarmerApi(profile?.id ? `/api/statements/statement/history/?farmer_id=${profile.id}` : null)
  const { data: deliveries, loading: delLoading, error: delError } = useFarmerApi('/api/deliveries/?page=1&page_size=10&ordering=-date_delivered')
  const { data: loans, loading: loansLoading, error: loansError } = useFarmerApi('/api/loans/?status=ACTIVE')

  const loading = profileLoading || historyLoading || delLoading || loansLoading
  const apiError = profileError || historyError || delError || loansError

  const payments = history?.payments || []
  const lastPayment = payments[0] || null
  const activeLoan = loans?.results?.[0] || loans?.[0] || null
  const deliveryList = deliveries?.results || deliveries || []
  const deliveryCount = deliveries?.count || deliveryList.length
  const todayDeliveries = deliveryList.filter(d => isToday(d.date_delivered)).length
  const todayVolume = deliveryList
    .filter(d => isToday(d.date_delivered))
    .reduce((sum, d) => sum + (d.quantity_kg || d.volume_litres || 0), 0)

  // Group deliveries by product type for quick summary
  const productSummary = deliveryList.reduce((acc, d) => {
    const key = d.product_type || 'Other'
    acc[key] = (acc[key] || 0) + (d.quantity_kg || d.volume_litres || 0)
    return acc
  }, {})

  const handleLatestStatement = async () => {
    try {
      const res = await apiFetch('/api/statements/statement/latest/?download=true')
      if (!res.ok) { showToast({ type: 'error', message: t('noStatement') }); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      URL.revokeObjectURL(url)
    } catch { showToast({ type: 'error', message: t('failedToLoad') }) }
  }

  if (loading) {
    return (
      <div>
        <div className="flex justify-between items-center mb-6">
          <div className="animate-pulse bg-gray-200 rounded-lg h-8 w-40" />
          <NotificationBell viewAllPath="/farmer/notifications" />
        </div>
        <KpiSkeleton />
        <div className="mt-6 space-y-3"><CardSkeleton /><CardSkeleton /></div>
      </div>
    )
  }

  if (apiError) {
    return <ErrorState message={apiError} action={{ label: t('retry'), onClick: refetchProfile }} />
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-xl font-bold text-on-surface">
            {t('hello')}, {profile?.first_name || user?.first_name || t('farmer')}!
          </h1>
          {profile?.member_number && (
            <p className="text-xs text-on-surface-variant mt-0.5">
              {t('memberNumber')}: {profile.member_number} · {profile?.county || t('yourCounty')}
            </p>
          )}
        </div>
        <NotificationBell viewAllPath="/farmer/notifications" />
      </div>

      {/* Today's deliveries summary */}
      {todayDeliveries > 0 && (
        <div className="bg-primary-container/20 border border-primary-container rounded-xl p-4 mb-5">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-primary" aria-hidden="true">today</span>
            <p className="text-xs font-semibold text-primary uppercase tracking-wide">{t('today')}</p>
          </div>
          <div className="flex justify-between items-end">
            <div>
              <p className="text-2xl font-bold text-primary">{todayDeliveries} {t('deliveries')}</p>
              <p className="text-sm text-on-surface-variant">{todayVolume} kg/L {t('collected')}</p>
            </div>
            <button onClick={() => navigate('/farmer/deliveries')} className="text-xs font-medium text-primary underline">
              {t('viewAll')}
            </button>
          </div>
        </div>
      )}

      {/* Key metrics */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <button onClick={() => navigate('/farmer/deliveries')} className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center cursor-pointer hover:shadow-md transition-shadow">
          <p className="text-xs text-on-surface-variant mb-1">{t('totalDeliveries')}</p>
          <p className="text-xl font-bold text-primary">{deliveryCount}</p>
        </button>
        <button onClick={() => navigate('/farmer/payments')} className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center cursor-pointer hover:shadow-md transition-shadow">
          <p className="text-xs text-on-surface-variant mb-1">{t('lastPayment')}</p>
          <p className="text-lg font-bold text-on-surface">{lastPayment ? formatKes(lastPayment.net_amount) : '-'}</p>
          {lastPayment && <p className="text-[10px] text-on-surface-variant mt-0.5">{lastPayment.status}</p>}
        </button>
        <button onClick={() => navigate('/farmer/loans')} className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center cursor-pointer hover:shadow-md transition-shadow">
          <p className="text-xs text-on-surface-variant mb-1">{t('activeLoan')}</p>
          <p className="text-lg font-bold text-warning">{activeLoan ? formatKes(activeLoan.amount_principal) : '-'}</p>
          {activeLoan && <p className="text-[10px] text-on-surface-variant mt-0.5">{activeLoan.installments_paid || 0}/{activeLoan.number_of_installments}</p>}
        </button>
      </div>

      {/* Product breakdown (if multiple product types) */}
      {Object.keys(productSummary).length > 1 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-on-surface mb-2">{t('yourProduce')}</h3>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(productSummary).map(([type, qty]) => (
              <div key={type} className="bg-surface-container rounded-lg border border-outline-variant px-3 py-2 text-xs">
                <span className="font-medium capitalize">{type.replace(/_/g, ' ')}</span>
                <span className="text-on-surface-variant ml-1">{qty} kg/L</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action cards */}
      <div className="space-y-3 mb-6">
        <button onClick={handleLatestStatement} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-primary-container/20 transition-colors text-left">
          <div className="w-10 h-10 rounded-xl bg-primary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-primary" aria-hidden="true">description</span>
          </div>
          <div>
            <p className="font-semibold text-sm text-on-surface">{t('latestStatement')}</p>
            <p className="text-xs text-on-surface-variant">{t('seeStatement')}</p>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant ml-auto" aria-hidden="true">chevron_right</span>
        </button>

        <button onClick={() => navigate('/farmer/chat')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-info-container/20 transition-colors text-left">
          <div className="w-10 h-10 rounded-xl bg-info-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-info" aria-hidden="true">smart_toy</span>
          </div>
          <div>
            <p className="font-semibold text-sm text-on-surface">{t('chatWithAI')}</p>
            <p className="text-xs text-on-surface-variant">{t('askAbout')}</p>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant ml-auto" aria-hidden="true">chevron_right</span>
        </button>

        {activeLoan && (
          <button onClick={() => navigate('/farmer/loans')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-warning-container/20 transition-colors text-left">
            <div className="w-10 h-10 rounded-xl bg-warning-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-warning" aria-hidden="true">account_balance_wallet</span>
            </div>
            <div>
              <p className="font-semibold text-sm text-on-surface">{t('activeLoan')}: {formatKes(activeLoan.amount_principal)}</p>
              <p className="text-xs text-on-surface-variant">{activeLoan.installments_paid || 0}/{activeLoan.number_of_installments} {t('installmentsPaid')}</p>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant ml-auto" aria-hidden="true">chevron_right</span>
          </button>
        )}

        {lastPayment && (
          <button onClick={() => navigate('/farmer/payments')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-success-container/20 transition-colors text-left">
            <div className="w-10 h-10 rounded-xl bg-success-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-success" aria-hidden="true">payments</span>
            </div>
            <div>
              <p className="font-semibold text-sm text-on-surface">{lastPayment.cycle_name || t('lastPayment')}</p>
              <p className="text-xs text-on-surface-variant">{formatKes(lastPayment.net_amount)} {t('net')} — {lastPayment.status}</p>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant ml-auto" aria-hidden="true">chevron_right</span>
          </button>
        )}
      </div>

      {/* Farmer profile quick view */}
      <div className="bg-primary/5 rounded-xl p-4 mb-4">
        <p className="text-xs text-on-surface-variant">{t('memberNumber')}: {profile?.member_number || '-'}</p>
        <p className="text-xs text-on-surface-variant">{t('county')}: {profile?.county || '-'} · {t('village')}: {profile?.village || '-'}</p>
        <p className="text-xs text-on-surface-variant mt-1">{t('paymentMethod')}: {profile?.payment_method || '-'} {profile?.mpesa_number ? '· ' + profile.mpesa_number : ''}</p>
      </div>
    </div>
  )
}
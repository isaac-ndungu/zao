import { useNavigate } from 'react-router-dom'
import useFarmerApi from '../hooks/useFarmerApi'
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

export default function FarmerDashboard() {
  const navigate = useNavigate()
  const { user } = useFarmerAuth()
  const { showToast } = useToast()
  const { data: profile, loading: profileLoading } = useFarmerApi('/api/farmers/me/')
  const { data: history, loading: historyLoading } = useFarmerApi(profile?.id ? `/api/statements/statement/history/?farmer_id=${profile.id}` : null)
  const { data: deliveries, loading: delLoading } = useFarmerApi('/api/deliveries/?page=1&page_size=5&ordering=-date_delivered')
  const { data: loans, loading: loansLoading } = useFarmerApi('/api/loans/?status=ACTIVE')

  const loading = profileLoading || historyLoading || delLoading || loansLoading

  const payments = history?.payments || []
  const lastPayment = payments[0] || null
  const activeLoan = loans?.results?.[0] || loans?.[0] || null
  const deliveryCount = deliveries?.count || deliveries?.length || 0

  const handleLatestStatement = async () => {
    try {
      const res = await apiFetch('/api/statements/statement/latest/?download=true')
      if (!res.ok) { showToast({ type: 'error', message: 'No statement available yet.' }); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      URL.revokeObjectURL(url)
    } catch { showToast({ type: 'error', message: 'Failed to load statement.' }) }
  }

  if (loading) {
    return (
      <div>
        <div className="flex justify-between items-center mb-6">
          <div className="animate-pulse bg-gray-200 rounded-lg h-8 w-40" />
          <NotificationBell />
        </div>
        <KpiSkeleton />
        <div className="mt-6 space-y-3"><CardSkeleton /><CardSkeleton /></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-xl font-bold text-on-surface">
            {t('hello')}, {profile?.first_name || user?.first_name || 'Farmer'}!
          </h1>
          {profile?.member_number && (
            <p className="text-xs text-on-surface-variant mt-0.5">
              {t('memberNumber')}: {profile.member_number}
            </p>
          )}
        </div>
        <NotificationBell />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center">
          <p className="text-xs text-on-surface-variant mb-1">{t('totalDeliveries')}</p>
          <p className="text-xl font-bold text-primary">{deliveryCount}</p>
        </div>
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center" onClick={() => navigate('/farmer/payments')}>
          <p className="text-xs text-on-surface-variant mb-1">{t('lastPayment')}</p>
          <p className="text-lg font-bold text-on-surface">{lastPayment ? formatKes(lastPayment.net_amount) : '-'}</p>
          {lastPayment && <p className="text-[10px] text-on-surface-variant mt-0.5">{lastPayment.status}</p>}
        </div>
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4 text-center" onClick={() => navigate('/farmer/loans')}>
          <p className="text-xs text-on-surface-variant mb-1">{t('activeLoan')}</p>
          <p className="text-lg font-bold text-warning">{activeLoan ? formatKes(activeLoan.amount_principal) : '-'}</p>
          {activeLoan && <p className="text-[10px] text-on-surface-variant mt-0.5">{activeLoan.status}</p>}
        </div>
      </div>

      <div className="space-y-3 mb-6">
        <button onClick={handleLatestStatement} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-primary-container/20 transition-colors text-left">
          <div className="w-10 h-10 rounded-xl bg-primary-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-primary">description</span>
          </div>
          <div>
            <p className="font-semibold text-sm text-on-surface">{t('latestStatement')}</p>
            <p className="text-xs text-on-surface-variant">{t('seeStatement')}</p>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
        </button>

        <button onClick={() => navigate('/farmer/chat')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-primary-container/20 transition-colors text-left">
          <div className="w-10 h-10 rounded-xl bg-info-container flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-info">smart_toy</span>
          </div>
          <div>
            <p className="font-semibold text-sm text-on-surface">{t('chatWithAI')}</p>
            <p className="text-xs text-on-surface-variant">Ask about payments, deliveries, and more</p>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
        </button>

        {activeLoan && (
          <button onClick={() => navigate('/farmer/loans')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-warning-container/20 transition-colors text-left">
            <div className="w-10 h-10 rounded-xl bg-warning-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-warning">account_balance_wallet</span>
            </div>
            <div>
              <p className="font-semibold text-sm text-on-surface">{t('activeLoan')}: {formatKes(activeLoan.amount_principal)}</p>
              <p className="text-xs text-on-surface-variant">{activeLoan.installments_paid || 0}/{activeLoan.number_of_installments} installments paid</p>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
          </button>
        )}

        {lastPayment && (
          <button onClick={() => navigate('/farmer/payments')} className="bg-surface-container rounded-xl border border-outline-variant w-full flex items-center gap-4 p-4 hover:bg-success-container/20 transition-colors text-left">
            <div className="w-10 h-10 rounded-xl bg-success-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-success">payments</span>
            </div>
            <div>
              <p className="font-semibold text-sm text-on-surface">{lastPayment.cycle_name || 'Last Payment'}</p>
              <p className="text-xs text-on-surface-variant">{formatKes(lastPayment.net_amount)} net — {lastPayment.status}</p>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant ml-auto">chevron_right</span>
          </button>
        )}
      </div>

      <div className="bg-primary/5 rounded-xl p-4 mb-4">
        <p className="text-xs text-on-surface-variant mb-1">{t('memberNumber')}: {profile?.member_number || '-'}</p>
        <p className="text-xs text-on-surface-variant">{t('county')}: {profile?.county || '-'} | {t('village')}: {profile?.village || '-'}</p>
      </div>
    </div>
  )
}

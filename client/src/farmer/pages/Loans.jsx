import { useState } from 'react'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { ListSkeleton } from '../components/LoadingSkeleton'
import { t } from '../i18n'
import { useFarmerAuth } from '../context/FarmerAuthContext'

function formatKes(n) { return n ? `KES ${Number(n).toLocaleString()}` : 'KES 0' }

const statusColors = {
  PENDING: 'bg-warning-container text-warning',
  ACTIVE: 'bg-info-container text-info',
  APPROVED: 'bg-info-container text-info',
  DISBURSED: 'bg-success-container text-success',
  COMPLETED: 'bg-primary-container text-primary',
  DEFAULTED: 'bg-error-container text-error',
}

export default function FarmerLoans() {
  const { showToast } = useToast()
  const { user: farmerUser } = useFarmerAuth()
  const [selected, setSelected] = useState(null)
  const [showApply, setShowApply] = useState(false)
  const [form, setForm] = useState({ amount_principal: '', interest_rate: '10', number_of_installments: '12', notes: '' })
  const [saving, setSaving] = useState(false)
  const { data, loading, error, refetch } = useFarmerApi('/api/loans/?ordering=-created_at')

  const loans = data?.results || data || []
  const activeLoan = loans.find(l => l.status === 'ACTIVE' || l.status === 'DISBURSED')

  const handleApply = async (e) => {
    e.preventDefault()
    if (!farmerUser?.id) {
      showToast({ type: 'error', message: 'Could not determine farmer profile. Please try logging in again.' })
      return
    }
    setSaving(true)
    try {
      const res = await apiFetch('/api/loans/', {
        method: 'POST',
        body: JSON.stringify({
          farmer: farmerUser.id,
          amount_principal: parseFloat(form.amount_principal),
          interest_rate: parseFloat(form.interest_rate),
          number_of_installments: parseInt(form.number_of_installments),
          notes: form.notes,
        }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || t('applyFailed')) }
      showToast({ type: 'success', message: t('applicationSubmitted') })
      setShowApply(false)
      setForm({ amount_principal: '', interest_rate: '10', number_of_installments: '12', notes: '' })
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  if (error) return <ErrorState message={error} action={{ label: t('retry'), onClick: refetch }} />
  if (loading) return <div><h2 className="text-lg font-bold mb-4">{t('loans')}</h2><ListSkeleton count={3} /></div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">{t('loans')} {loans.length > 0 && <span className="text-sm font-normal text-on-surface-variant">({loans.length})</span>}</h2>
        <button onClick={() => setShowApply(true)} className="bg-primary text-on-primary px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:opacity-80">
          {t('applyLoan')}
        </button>
      </div>

      {activeLoan && (
        <div className="bg-warning-container/20 border border-warning-container rounded-xl p-4 mb-4">
          <p className="text-xs font-semibold text-warning mb-1">{t('activeLoan')}</p>
          <p className="text-xl font-bold">{formatKes(activeLoan.amount_principal)}</p>
          {activeLoan.number_of_installments && (
            <div className="mt-2">
              <div className="flex justify-between text-xs mb-1">
                <span>{t('repaymentProgress')}</span>
                <span>{activeLoan.installments_paid || 0}/{activeLoan.number_of_installments}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-success h-2 rounded-full" style={{ width: `${((activeLoan.installments_paid || 0) / activeLoan.number_of_installments) * 100}%` }} />
              </div>
            </div>
          )}
          <button onClick={() => setSelected(activeLoan)} className="mt-3 text-xs text-primary underline">
            {t('viewDetails')}
          </button>
        </div>
      )}

      {loans.length === 0 ? (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-3">account_balance_wallet</span>
          <p className="text-on-surface-variant mb-4">{t('noLoans')}</p>
          <button onClick={() => setShowApply(true)} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80">
            {t('applyLoan')}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {loans.map((loan) => (
            <button key={loan.id} onClick={() => setSelected(selected?.id === loan.id ? null : loan)} className="bg-surface-container rounded-xl border border-outline-variant p-4 w-full text-left">
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-1 ${
                  loan.status === 'COMPLETED' ? 'bg-success-container' : loan.status === 'DEFAULTED' ? 'bg-error-container' : 'bg-warning-container'
                }`}>
                  <span className={`material-symbols-outlined ${
                    loan.status === 'COMPLETED' ? 'text-success' : loan.status === 'DEFAULTED' ? 'text-error' : 'text-warning'
                  }`}>account_balance_wallet</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-sm">{formatKes(loan.amount_principal)}</p>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[loan.status] || 'bg-gray-200 text-gray-500'}`}>
                      {loan.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                    <span>{loan.interest_rate}%</span>
                    <span>{loan.installments_paid || 0}/{loan.number_of_installments} {t('paid')}</span>
                    <span className="ml-auto">{loan.created_at ? new Date(loan.created_at).toLocaleDateString() : '-'}</span>
                  </div>
                  {selected?.id === loan.id && (
                    <div className="border-t border-outline-variant mt-3 pt-3 space-y-2">
                      {loan.total_repayable && <div className="flex justify-between text-xs"><span>{t('totalRepayable')}</span><span className="font-bold">{formatKes(loan.total_repayable)}</span></div>}
                      {loan.installment_amount && <div className="flex justify-between text-xs"><span>{t('installment')}</span><span className="font-bold">{formatKes(loan.installment_amount)}</span></div>}
                      {loan.guarantors?.length > 0 && (
                        <div>
                          <p className="text-xs text-on-surface-variant mb-1">{t('guarantors')}</p>
                          {loan.guarantors.map((g, i) => (
                            <p key={i} className="text-xs">{g.guarantor_name || `${t('guarantor')} #${i + 1}`}</p>
                          ))}
                        </div>
                      )}
                      {loan.notes && <p className="text-xs text-on-surface-variant">{t('notes')}: {loan.notes}</p>}
                    </div>
                  )}
                </div>
                <span className="material-symbols-outlined text-on-surface-variant text-xl mt-2">
                  {selected?.id === loan.id ? 'expand_less' : 'expand_more'}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {showApply && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-end" style={{ animation: 'fadeIn 0.2s' }} onClick={() => setShowApply(false)}>
          <div className="bg-surface-container rounded-t-2xl p-6 w-full max-h-[85vh] overflow-y-auto" style={{ animation: 'slideUp 0.3s ease-out' }} onClick={(e) => e.stopPropagation()}>
            <div className="w-10 h-1 bg-gray-300 rounded-full mx-auto my-3" />
            <h3 className="font-bold text-lg mb-4">{t('applyLoan')}</h3>
            <form onSubmit={handleApply} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('loanAmount')} (KES)</label>
                <input type="number" min="1" value={form.amount_principal} onChange={(e) => setForm(p => ({ ...p, amount_principal: e.target.value }))} required className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('interestRate')} (%)</label>
                <input type="number" step="0.1" min="0" value={form.interest_rate} onChange={(e) => setForm(p => ({ ...p, interest_rate: e.target.value }))} required className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('installments')}</label>
                <input type="number" min="1" max="60" value={form.number_of_installments} onChange={(e) => setForm(p => ({ ...p, number_of_installments: e.target.value }))} required className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('description')}</label>
                <textarea value={form.notes} onChange={(e) => setForm(p => ({ ...p, notes: e.target.value }))} rows={3} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" />
              </div>
              <div className="flex gap-3">
                <button type="submit" disabled={saving} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed flex-1">
                  {saving ? <span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full" /> : t('applyLoan')}
                </button>
                <button type="button" onClick={() => setShowApply(false)} className="bg-transparent border border-outline-variant px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:bg-gray-50 flex-1">
                  {t('cancel')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
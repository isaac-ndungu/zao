import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import useFarmerApi from '../hooks/useFarmerApi'
import ErrorState from '../../shared/components/ErrorState'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { CardSkeleton } from '../components/LoadingSkeleton'
import ConfirmModal from '../components/ConfirmModal'
import PickupLocationEditor from '../../shared/components/PickupLocationEditor'
import { t } from '../i18n'

export default function FarmerProfile() {
  const navigate = useNavigate()
  const { logout } = useFarmerAuth()
  const { showToast } = useToast()
  const { data: profile, loading, error, refetch } = useFarmerApi('/api/farmers/me/')

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [saving, setSaving] = useState(false)

  const startEdit = () => {
    setForm({
      phone_number: profile?.phone_number || '',
      email: profile?.email || '',
      village: profile?.village || '',
      ward: profile?.ward || '',
      sub_county: profile?.sub_county || '',
    })
    setEditing(true)
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await apiFetch('/api/farmers/me/', { method: 'PATCH', body: JSON.stringify(form) })
      if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || t('updateFailed')) }
      showToast({ type: 'success', message: t('profileUpdated') })
      setEditing(false)
      refetch()
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
    setLoggingOut(false)
    setShowLogoutConfirm(false)
  }

  if (error) return <ErrorState message={error} action={{ label: t('retry'), onClick: refetch }} />
  if (loading) return <div className="text-center py-12"><CardSkeleton lines={6} /></div>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-bold">{t('profile')}</h2>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/farmer/settings')} aria-label={t('settings')} className="p-1">
            <span className="material-symbols-outlined text-on-surface-variant" aria-hidden="true">settings</span>
          </button>
        </div>
      </div>

      <div className="text-center mb-6">
        <div className="w-20 h-20 rounded-full bg-primary-container flex items-center justify-center mx-auto mb-3">
          <span className="material-symbols-outlined text-primary text-3xl" aria-hidden="true">person</span>
        </div>
        <h3 className="font-bold text-lg">{profile?.first_name} {profile?.last_name}</h3>
        <p className="text-sm text-on-surface-variant">{t('memberNumber')}: {profile?.member_number}</p>
        <p className="text-xs text-on-surface-variant mt-1">{profile?.county}, {profile?.sub_county}</p>
      </div>

      {!editing ? (
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><p className="text-xs text-on-surface-variant">{t('phoneNumber')}</p><p className="text-sm font-medium">{profile?.phone_number || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('email')}</p><p className="text-sm font-medium">{profile?.email || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('county')}</p><p className="text-sm font-medium">{profile?.county || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('subCounty')}</p><p className="text-sm font-medium">{profile?.sub_county || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('ward')}</p><p className="text-sm font-medium">{profile?.ward || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('village')}</p><p className="text-sm font-medium">{profile?.village || '-'}</p></div>
          </div>
          <div className="border-t border-outline-variant pt-4 mt-4 space-y-3">
            <div><p className="text-xs text-on-surface-variant">{t('paymentMethod')}</p><p className="text-sm font-medium">{profile?.payment_method || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('mpesaNumber')}</p><p className="text-sm font-medium">{profile?.mpesa_number || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('bankName')}</p><p className="text-sm font-medium">{profile?.bank_name || '-'}</p></div>
            <div><p className="text-xs text-on-surface-variant">{t('bankAccount')}</p><p className="text-sm font-medium">{profile?.bank_account || '-'}</p></div>
          </div>
          <button onClick={startEdit} className="bg-transparent border border-outline-variant px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:bg-gray-50 w-full mt-2">
            {t('edit')}
          </button>
        </div>
      ) : (
        <div className="bg-surface-container rounded-xl border border-outline-variant p-4">
          <form onSubmit={handleSave} className="space-y-4">
            <div><label htmlFor="phone_number" className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('phoneNumber')}</label><input id="phone_number" value={form.phone_number} onChange={(e) => setForm(p => ({ ...p, phone_number: e.target.value }))} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
            <div><label htmlFor="email" className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('email')}</label><input id="email" value={form.email} onChange={(e) => setForm(p => ({ ...p, email: e.target.value }))} type="email" className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
            <div><label htmlFor="village" className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('village')}</label><input id="village" value={form.village} onChange={(e) => setForm(p => ({ ...p, village: e.target.value }))} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
            <div><label htmlFor="ward" className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('ward')}</label><input id="ward" value={form.ward} onChange={(e) => setForm(p => ({ ...p, ward: e.target.value }))} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
            <div><label htmlFor="sub_county" className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('subCounty')}</label><input id="sub_county" value={form.sub_county} onChange={(e) => setForm(p => ({ ...p, sub_county: e.target.value }))} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
            <div className="flex gap-3">
              <button type="submit" disabled={saving} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed flex-1">
                {saving ? <span aria-hidden="true" className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full" /> : t('save')}
              </button>
              <button type="button" onClick={() => setEditing(false)} className="bg-transparent border border-outline-variant px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:bg-gray-50 flex-1">
                {t('cancel')}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="mt-6 bg-surface-container rounded-xl border border-outline-variant p-4 space-y-3">
        <h3 className="text-base font-bold">{t('pickupLocation')}</h3>
        {profile?.latitude != null && profile?.longitude != null ? (
          <p className="text-label-sm text-on-surface-variant">
            {Number(profile.latitude).toFixed(5)}, {Number(profile.longitude).toFixed(5)}
          </p>
        ) : (
          <p className="text-label-sm text-on-surface-variant">{t('pickupLocationEmpty')}</p>
        )}
        <PickupLocationEditor
          farmerId={profile?.id}
          initial={profile?.latitude != null ? { latitude: profile.latitude, longitude: profile.longitude } : null}
          onSaved={() => refetch()}
          height="200px"
        />
      </div>

      <div className="mt-6">
        <button onClick={() => setShowLogoutConfirm(true)} className="bg-error text-white px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 w-full flex items-center justify-center gap-2">
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          {t('logout')}
        </button>
      </div>

      <ConfirmModal
        open={showLogoutConfirm}
        title={t('logout')}
        message={t('confirmLogout')}
        confirmLabel={t('logout')}
        cancelLabel={t('cancel')}
        loading={loggingOut}
        onConfirm={handleLogout}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </div>
  )
}
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { setLanguage, getLanguage, t } from '../i18n'

export default function FarmerSettings() {
  const navigate = useNavigate()
  const { logout } = useFarmerAuth()
  const { showToast } = useToast()
  const [lang, setLangState] = useState(getLanguage())
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', confirm_password: '' })
  const [saving, setSaving] = useState(false)

  const switchLang = (l) => {
    setLanguage(l)
    setLangState(l)
    showToast({ type: 'success', message: l === 'sw' ? 'Lugha imebadilishwa' : 'Language changed' })
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm_password) {
      showToast({ type: 'error', message: 'Passwords do not match.' })
      return
    }
    setSaving(true)
    try {
      const res = await apiFetch('/api/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ current_password: pwForm.old_password, new_password: pwForm.new_password }),
      })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed to change password') }
      showToast({ type: 'success', message: 'Password changed.' })
      setPwForm({ old_password: '', new_password: '', confirm_password: '' })
    } catch (err) { showToast({ type: 'error', message: err.message }) }
    finally { setSaving(false) }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/farmer/profile')} aria-label="Back to profile" className="p-1">
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <h2 className="text-lg font-bold">{t('settings')}</h2>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-3">{t('language')}</h3>
        <div className="flex gap-3">
          <button onClick={() => switchLang('en')} className={`inline-flex items-center px-4 py-2 rounded-full border-2 border-outline-variant bg-surface-container text-sm whitespace-nowrap min-h-[36px] active:bg-primary-container active:border-primary flex-1 justify-center ${lang === 'en' ? '!bg-primary-container !border-primary !text-primary' : ''}`}>English</button>
          <button onClick={() => switchLang('sw')} className={`inline-flex items-center px-4 py-2 rounded-full border-2 border-outline-variant bg-surface-container text-sm whitespace-nowrap min-h-[36px] active:bg-primary-container active:border-primary flex-1 justify-center ${lang === 'sw' ? '!bg-primary-container !border-primary !text-primary' : ''}`}>Kiswahili</button>
        </div>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-4">{t('changePassword')}</h3>
        <form onSubmit={handlePasswordChange} className="space-y-3">
          <div><label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('currentPassword')}</label><input value={pwForm.old_password} onChange={(e) => setPwForm(p => ({ ...p, old_password: e.target.value }))} type="password" required className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
          <div><label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('newPassword')}</label><input value={pwForm.new_password} onChange={(e) => setPwForm(p => ({ ...p, new_password: e.target.value }))} type="password" required minLength={8} className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
          <div><label className="block text-xs font-semibold text-on-surface-variant mb-1.5">{t('confirmPassword')}</label><input value={pwForm.confirm_password} onChange={(e) => setPwForm(p => ({ ...p, confirm_password: e.target.value }))} type="password" required className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px]" /></div>
          <button type="submit" disabled={saving} className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed w-full">{saving ? <span className="inline-block animate-spin h-5 w-5 border-2 border-outline-variant border-t-primary rounded-full" /> : t('changePassword')}</button>
        </form>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-2">{t('aboutZao')}</h3>
        <p className="text-xs text-on-surface-variant">Zao Farmer Management System</p>
        <p className="text-xs text-on-surface-variant">{t('version')} 1.0.0</p>
      </div>

      <button onClick={logout} className="bg-error text-white px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 w-full flex items-center justify-center gap-2">
        <span className="material-symbols-outlined">logout</span>
        {t('logout')}
      </button>
    </div>
  )
}

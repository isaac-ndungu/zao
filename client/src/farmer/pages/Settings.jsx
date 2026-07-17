import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFarmerAuth } from '../context/FarmerAuthContext'
import { apiFetch } from '../api/client'
import { useToast } from '../components/Toast'
import { setLanguage, getLanguage, t } from '../i18n'
import ConfirmModal from '../components/ConfirmModal'
import PasswordInput from '../../shared/components/PasswordInput'
import { useFormAction, formDataToObject, SubmitButton } from '../../shared/hooks/useFormAction'

export default function FarmerSettings() {
  const navigate = useNavigate()
  const { logout } = useFarmerAuth()
  const { showToast } = useToast()
  const [lang, setLangState] = useState(getLanguage())
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  const switchLang = (l) => {
    setLanguage(l)
    setLangState(l)
    showToast({ type: 'success', message: l === 'sw' ? 'Lugha imebadilishwa' : t('languageChanged') })
  }

  const { formAction: changePasswordAction } = useFormAction(async (prev, formData) => {
    const data = formDataToObject(formData)
    if (data.new_password !== data.confirm_password) {
      throw new Error(t('passwordsMismatch'))
    }
    const res = await apiFetch('/api/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({ current_password: data.current_password, new_password: data.new_password }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || t('passwordChangeFailed'))
    }
    showToast({ type: 'success', message: t('passwordChanged') })
    document.getElementById('password-change-form')?.reset()
    return { success: true }
  }, {})

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
    setLoggingOut(false)
    setShowLogoutConfirm(false)
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate('/farmer/profile')} aria-label={t('backToProfile')} className="p-1">
          <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
        </button>
        <h2 className="text-lg font-bold">{t('settings')}</h2>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-3">{t('language')}</h3>
        <div className="flex gap-3">
          <button onClick={() => switchLang('en')} className={`flex-1 inline-flex items-center justify-center px-4 py-2 rounded-full border-2 border-outline-variant text-sm min-h-[36px] ${lang === 'en' ? 'bg-primary-container border-primary text-primary' : ''}`}>
            English
          </button>
          <button onClick={() => switchLang('sw')} className={`flex-1 inline-flex items-center justify-center px-4 py-2 rounded-full border-2 border-outline-variant text-sm min-h-[36px] ${lang === 'sw' ? 'bg-primary-container border-primary text-primary' : ''}`}>
            Kiswahili
          </button>
        </div>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-4">{t('changePassword')}</h3>
        <form id="password-change-form" action={changePasswordAction} className="space-y-3">
          <PasswordInput
            id="id-current-password"
            name="current_password"
            label={t('currentPassword')}
            required
          />
          <PasswordInput
            id="id-new-password"
            name="new_password"
            label={t('newPassword')}
            required
            minLength={8}
          />
          <PasswordInput
            id="id-confirm-password"
            name="confirm_password"
            label={t('confirmPassword')}
            required
          />
          <SubmitButton className="bg-primary text-on-primary px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 w-full">
            {t('changePassword')}
          </SubmitButton>
        </form>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <h3 className="font-semibold text-sm mb-2">{t('helpSupport')}</h3>
        <a href="tel:+254700000000" className="flex items-center gap-3 py-2 text-sm hover:bg-primary-container/10 rounded-lg px-2 -mx-2">
          <span className="material-symbols-outlined" aria-hidden="true">call</span> {t('callSupport')}
        </a>
        <a href="https://wa.me/254700000000" target="_blank" rel="noreferrer" className="flex items-center gap-3 py-2 text-sm hover:bg-primary-container/10 rounded-lg px-2 -mx-2">
          <span className="material-symbols-outlined" aria-hidden="true">chat</span> WhatsApp
        </a>
      </div>

      <div className="bg-surface-container rounded-xl border border-outline-variant p-4 mb-4">
        <p className="text-xs text-on-surface-variant">{t('zaoFarmerSystem')}</p>
        <p className="text-xs text-on-surface-variant">{t('version')} 1.0.0</p>
      </div>

      <button onClick={() => setShowLogoutConfirm(true)} className="bg-error text-white px-6 py-3 rounded-xl text-sm font-semibold min-h-[44px] hover:opacity-80 w-full flex items-center justify-center gap-2">
        <span className="material-symbols-outlined" aria-hidden="true">logout</span>
        {t('logout')}
      </button>

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

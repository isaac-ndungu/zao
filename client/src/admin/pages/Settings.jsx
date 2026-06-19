import { useAdminAuth } from '../hooks/useAdminAuth'
import { useState } from 'react'

export default function Settings() {
  const { user } = useAdminAuth()
  const [saved, setSaved] = useState(false)

  const handleSave = (e) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="max-w-2xl">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Settings</h2>
        <p className="text-on-surface-variant font-body-md">Manage your admin profile and preferences.</p>
      </header>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-6">Profile</h4>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-label-md font-bold text-on-surface-variant mb-1">First Name</label>
              <input
                type="text"
                defaultValue={user?.first_name || ''}
                className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              />
            </div>
            <div>
              <label className="block text-label-md font-bold text-on-surface-variant mb-1">Last Name</label>
              <input
                type="text"
                defaultValue={user?.last_name || ''}
                className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
              />
            </div>
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Email</label>
            <input
              type="email"
              defaultValue={user?.email || ''}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            />
          </div>
          <div>
            <label className="block text-label-md font-bold text-on-surface-variant mb-1">Phone</label>
            <input
              type="tel"
              defaultValue={user?.phone_number || ''}
              className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-body-md text-on-surface"
            />
          </div>
          <div className="pt-2">
            <button
              type="submit"
              className="px-6 py-2 bg-primary text-on-primary rounded-lg font-bold text-label-md hover:bg-primary/90 transition-colors"
            >
              {saved ? 'Saved!' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Account</h4>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-outline-variant/50">
            <div>
              <p className="font-body-md font-medium text-on-surface">Role</p>
              <p className="text-label-md text-on-surface-variant">{user?.role || 'Admin'}</p>
            </div>
            <span className="px-3 py-1 bg-primary-container text-on-primary-container rounded-full text-[11px] font-bold uppercase">Verified</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-body-md font-medium text-on-surface">Two-Factor Authentication</p>
              <p className="text-label-md text-on-surface-variant">Add an extra layer of security</p>
            </div>
            <button className="px-4 py-1.5 border border-primary text-primary rounded-lg text-label-md font-bold hover:bg-primary/5 transition-colors">
              Enable
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

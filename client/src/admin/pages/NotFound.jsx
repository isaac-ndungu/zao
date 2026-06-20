import { useNavigate } from 'react-router-dom'

export default function AdminNotFound() {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <span className="material-symbols-outlined text-[64px] text-outline-variant mb-4">block</span>
      <h2 className="font-headline-lg text-display-md text-on-surface mb-2">Page Not Found</h2>
      <p className="text-on-surface-variant font-body-md mb-6">The page you are looking for does not exist.</p>
      <button
        onClick={() => navigate('/admin/dashboard')}
        className="px-6 py-2.5 rounded-lg bg-primary text-white text-label-md font-bold hover:bg-primary/90 transition-colors"
      >
        Back to Dashboard
      </button>
    </div>
  )
}

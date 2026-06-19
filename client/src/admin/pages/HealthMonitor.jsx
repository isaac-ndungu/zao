import { useState, useEffect } from 'react'
import { apiFetch } from '../api/client'
import KpiCard from '../components/common/KpiCard'

function StatusIndicator({ ok, label }) {
  return (
    <div className={`flex items-center gap-3 p-4 rounded-xl border ${ok ? 'bg-primary-container/30 border-primary-container' : 'bg-error-container border-error-container'}`}>
      <span className={`w-3 h-3 rounded-full ${ok ? 'bg-primary' : 'bg-error'}`} />
      <div>
        <p className="font-body-md font-medium text-on-surface">{label}</p>
        <p className={`text-label-md ${ok ? 'text-primary' : 'text-error'}`}>{ok ? 'Operational' : 'Down'}</p>
      </div>
    </div>
  )
}

export default function HealthMonitor() {
  const [health, setHealth] = useState(null)
  const [migrations, setMigrations] = useState(null)
  const [celery, setCelery] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      try {
        const [h, m, c] = await Promise.all([
          apiFetch('/api/admin/health/').catch(() => ({ db: false, redis: false, celery: false, worker_count: 0 })),
          apiFetch('/api/admin/migration-health/').catch(() => ({ up_to_date: false, count: -1, unapplied_migrations: [] })),
          apiFetch('/api/admin/celery/tasks/').catch(() => ({ active_count: 0, reserved_count: 0, scheduled_count: 0, tasks: { active: [], reserved: [], scheduled: [] } })),
        ])
        setHealth(h)
        setMigrations(m)
        setCelery(c)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
  }

  if (error) {
    return <div className="bg-error-container text-error p-4 rounded-xl">Failed to load health data: {error}</div>
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">System Health</h2>
        <p className="text-on-surface-variant font-body-md">Monitor backend services, database migrations, and task queues.</p>
      </header>

      {/* Service Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatusIndicator ok={health?.db} label="Database" />
        <StatusIndicator ok={health?.redis} label="Redis" />
        <StatusIndicator ok={health?.celery} label="Celery" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Worker Info */}
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Celery Workers</h4>
          {health?.worker_count > 0 ? (
            <div className="flex items-center gap-3 p-4 bg-surface-container rounded-lg">
              <span className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-headline-sm">
                {health.worker_count}
              </span>
              <div>
                <p className="font-body-md font-medium text-on-surface">Active Workers</p>
                <p className="text-label-md text-on-surface-variant">Processing tasks in the queue</p>
              </div>
            </div>
          ) : (
            <p className="text-on-surface-variant text-body-md">No worker information available.</p>
          )}
        </div>

        {/* Migration Health */}
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">DB Migration Health</h4>
          {migrations ? (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <StatusIndicator ok={migrations.up_to_date} label="Migrations Status" />
              </div>
              {migrations.unapplied_migrations?.length > 0 && (
                <div>
                  <p className="text-label-md font-bold text-on-surface-variant mb-2">Unapplied Migrations ({migrations.count})</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {migrations.unapplied_migrations.map((m, i) => (
                      <p key={i} className="text-[11px] font-data-mono text-on-surface-variant px-3 py-1 bg-surface-container rounded">{m}</p>
                    ))}
                  </div>
                </div>
              )}
              {migrations.count === 0 && (
                <p className="text-body-md text-primary font-medium">All migrations are up to date.</p>
              )}
            </div>
          ) : (
            <p className="text-on-surface-variant text-body-md">No migration data available.</p>
          )}
        </div>
      </div>

      {/* Celery Task Queues */}
      {celery && (
        <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl">
          <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Task Queues</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <KpiCard icon="play_circle" label="Active" value={celery.active_count || 0} highlighted={celery.active_count > 0} />
            <KpiCard icon="pause_circle" label="Reserved" value={celery.reserved_count || 0} />
            <KpiCard icon="schedule" label="Scheduled" value={celery.scheduled_count || 0} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['active', 'reserved', 'scheduled'].map((queue) => {
              const tasks = celery.tasks?.[queue] || []
              return (
                <div key={queue}>
                  <p className="text-label-md font-bold text-on-surface-variant uppercase mb-2">{queue} ({tasks.length})</p>
                  {tasks.length === 0 ? (
                    <p className="text-label-md text-on-surface-variant">No {queue} tasks.</p>
                  ) : (
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {tasks.slice(0, 10).map((task, i) => (
                        <div key={i} className="p-2 bg-surface-container rounded-lg text-[11px]">
                          <p className="font-data-mono text-on-surface truncate">{task.task_name || task.name || 'Unknown task'}</p>
                          <p className="text-on-surface-variant truncate">ID: {task.task_id?.slice(0, 12)}...</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

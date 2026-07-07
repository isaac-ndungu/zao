import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../api/client'
import KpiCard from '../components/common/KpiCard'
import { CardSkeleton } from '../components/common/Skeleton'

// Status indicator with animated pulse when operational
function StatusIndicator({ ok, label }) {
  return (
    <div
      className={`flex items-center gap-4 p-5 rounded-2xl border transition-all ${
        ok
          ? 'bg-primary-container/20 border-primary-container/40'
          : 'bg-error-container/20 border-error-container/40'
      }`}
    >
      <div className="relative flex items-center justify-center">
        <span
          className={`w-4 h-4 rounded-full ${ok ? 'bg-primary animate-pulse' : 'bg-error'}`}
        />
        {ok && (
          <span className="absolute inset-0 w-4 h-4 rounded-full bg-primary opacity-20 animate-ping" />
        )}
      </div>
      <div>
        <p className="text-sm font-semibold text-on-surface">{label}</p>
        <p className={`text-xs font-medium ${ok ? 'text-primary' : 'text-error'}`}>
          {ok ? 'Operational' : 'Down'}
        </p>
      </div>
    </div>
  )
}

// Migration list item with icon
function MigrationItem({ name }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-surface-container/70 border border-outline-variant/20">
      <span className="material-symbols-outlined text-[16px] text-on-surface-variant" aria-hidden="true">database</span>
      <code className="text-[11px] font-mono text-on-surface-variant truncate">{name}</code>
    </div>
  )
}

export default function HealthMonitor() {
  const [health, setHealth] = useState(null)
  const [migrations, setMigrations] = useState(null)
  const [celery, setCelery] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const intervalRef = useRef(null)

  const fetchAll = async () => {
    try {
      const [h, m, c] = await Promise.all([
        apiFetch('/api/admin/health/')
          .then((r) => r.json())
          .catch(() => ({ db: false, redis: false, celery: false, worker_count: 0 })),
        apiFetch('/api/admin/migration-health/')
          .then((r) => r.json())
          .catch(() => ({ up_to_date: false, count: -1, unapplied_migrations: [] })),
        apiFetch('/api/admin/celery/tasks/')
          .then((r) => r.json())
          .catch(() => ({
            active_count: 0,
            reserved_count: 0,
            scheduled_count: 0,
            tasks: { active: [], reserved: [], scheduled: [] },
          })),
      ])
      setHealth(h)
      setMigrations(m)
      setCelery(c)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    const initial = async () => {
      setLoading(true)
      await fetchAll()
      setLoading(false)
    }
    initial()
  }, [])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchAll, 30000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [autoRefresh])

  if (loading) {
    return (
      <div className="space-y-6">
        <header className="mb-6">
          <div className="animate-pulse h-8 w-48 bg-gray-200 rounded-lg mb-2" />
          <div className="animate-pulse h-4 w-72 bg-gray-200 rounded-lg" />
        </header>
        <CardSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-error-container/30 border border-error-container/40 text-error p-4 rounded-2xl">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-xl" aria-hidden="true">error</span>
          <p className="font-medium">Failed to load health data: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
          <h2 className="text-3xl font-bold text-on-surface tracking-tight">System Health</h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-on-surface-variant">Auto‑refresh</span>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              aria-label={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
              aria-pressed={autoRefresh}
              className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${
                autoRefresh ? 'bg-primary' : 'bg-surface-container-high'
              }`}
            >
              <span
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-200 ${
                  autoRefresh ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        </div>
        <p className="text-sm text-on-surface-variant max-w-2xl">
          Monitor backend services, database migrations, and task queues in real‑time.
        </p>
      </header>

      {/* Core Services */}
      <section className="mb-8">
        <h3 className="text-lg font-semibold text-on-surface mb-4">Core Services</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatusIndicator ok={health?.db} label="Database" />
          <StatusIndicator ok={health?.redis} label="Redis" />
          <StatusIndicator ok={health?.celery} label="Celery" />
        </div>
      </section>

      {/* Workers & Migrations */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Celery Workers */}
        <div className="bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-semibold text-on-surface">Celery Workers</h4>
            {health?.worker_count > 0 && (
              <span className="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold">
                {health.worker_count} active
              </span>
            )}
          </div>
          {health?.worker_count > 0 ? (
            <div className="flex items-center gap-4 p-4 rounded-xl bg-primary/5 border border-primary/10">
              <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary text-xl" aria-hidden="true">engineering</span>
              </div>
              <div>
                <p className="text-2xl font-bold text-on-surface">{health.worker_count}</p>
                <p className="text-sm text-on-surface-variant">Workers processing tasks</p>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-sm text-on-surface-variant">
              No worker information available.
            </div>
          )}
        </div>

        {/* DB Migration Health */}
        <div className="bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <h4 className="text-base font-semibold text-on-surface mb-4">Migration Health</h4>
          {migrations ? (
            <>
              <div className="mb-4">
                <StatusIndicator ok={migrations.up_to_date} label="Migrations" />
              </div>
              {migrations.count > 0 && migrations.unapplied_migrations?.length > 0 ? (
                <div>
                  <p className="text-sm font-semibold text-on-surface-variant mb-3">
                    Unapplied migrations ({migrations.count})
                  </p>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {migrations.unapplied_migrations.map((m, i) => (
                      <MigrationItem key={i} name={m} />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-success-container/10 border border-success/20 rounded-xl flex items-center gap-3">
                  <span className="material-symbols-outlined text-success text-xl" aria-hidden="true">check_circle</span>
                  <p className="text-sm font-medium text-success">All migrations are up to date.</p>
                </div>
              )}
            </>
          ) : (
            <div className="p-6 text-center text-sm text-on-surface-variant">
              No migration data available.
            </div>
          )}
        </div>
      </section>

      {/* Celery Task Queues */}
      {celery && (
        <section className="bg-surface-container rounded-2xl border border-outline-variant/40 p-6 shadow-sm">
          <h4 className="text-base font-semibold text-on-surface mb-4">Task Queues</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <KpiCard
              icon="play_circle"
              label="Active"
              value={celery.active_count || 0}
              highlighted={celery.active_count > 0}
            />
            <KpiCard icon="pause_circle" label="Reserved" value={celery.reserved_count || 0} />
            <KpiCard icon="schedule" label="Scheduled" value={celery.scheduled_count || 0} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {['active', 'reserved', 'scheduled'].map((queue) => {
              const tasks = celery.tasks?.[queue] || []
              return (
                <div key={queue} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-on-surface capitalize">{queue}</p>
                    <span className="text-xs font-medium text-on-surface-variant bg-surface-container-high px-2 py-0.5 rounded-full">
                      {tasks.length}
                    </span>
                  </div>
                  {tasks.length === 0 ? (
                    <div className="p-4 bg-surface-container-highest rounded-xl text-center text-xs text-on-surface-variant">
                      No {queue} tasks.
                    </div>
                  ) : (
                    <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                      {tasks.slice(0, 10).map((task, i) => (
                        <div
                          key={i}
                          className="p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/20 hover:bg-surface-container transition-colors"
                        >
                          <p className="text-xs font-mono text-on-surface truncate">
                            {task.task_name || task.name || 'Unknown task'}
                          </p>
                          <p className="text-[10px] text-on-surface-variant mt-0.5 truncate">
                            ID: {task.task_id?.slice(0, 12)}...
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
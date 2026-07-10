import DisputesTable from '../../shared/components/DisputesTable'

export default function ManagerDisputes() {
  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-on-surface mb-1">Disputes</h1>
        <p className="text-sm text-on-surface-variant">Review and resolve grade disputes from farmers</p>
      </header>

      <DisputesTable
        showResolve={true}
        showGrade={true}
        readOnly={false}
        title="Grade Disputes"
        emptyMessage="No disputes to review."
      />
    </div>
  )
}

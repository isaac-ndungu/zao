import DisputesTable from '../../shared/components/DisputesTable'

export default function AccountantDisputes() {
  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-on-surface mb-1">Disputes</h1>
        <p className="text-sm text-on-surface-variant">View grade disputes for audit and payment reconciliation</p>
      </header>

      <DisputesTable
        showResolve={false}
        showGrade={true}
        readOnly={true}
        title="Grade Disputes"
        emptyMessage="No disputes on record."
      />
    </div>
  )
}

import DisputesTable from '../../shared/components/DisputesTable'

export default function AdminDisputes() {
  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-on-surface mb-1">Disputes</h1>
        <p className="text-sm text-on-surface-variant">View and manage all grade disputes across cooperatives</p>
      </header>

      <DisputesTable
        showResolve={true}
        showGrade={true}
        readOnly={false}
        title="All Disputes"
        emptyMessage="No disputes found."
      />
    </div>
  )
}

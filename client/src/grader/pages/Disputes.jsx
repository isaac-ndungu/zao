import DisputesTable from '../../shared/components/DisputesTable'

export default function GraderDisputes() {
  return (
    <div className="max-w-7xl mx-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-on-surface mb-1">Disputes</h1>
        <p className="text-sm text-on-surface-variant">View disputed grades and their outcomes</p>
      </header>

      <DisputesTable
        showResolve={false}
        showGrade={true}
        readOnly={true}
        title="Disputed Grades"
        emptyMessage="No disputed grades."
      />
    </div>
  )
}

export default function Support() {
  const faqs = [
    { q: 'How do I create a new user?', a: 'Navigate to the User Management page via the search bar. Click the "Invite User" button and fill in the required details.' },
    { q: 'How do I process a payment cycle?', a: 'Go to Financials, select a payment cycle in "Draft" status, verify the data, and click "Compute" to progress it through the pipeline.' },
    { q: 'How do I force a delivery status change?', a: 'In Produce Receipts, find the delivery, click the "more_vert" icon, and select "Force Status". Choose the new status from the dropdown.' },
    { q: 'How do I restore a soft-deleted record?', a: 'Visit the Trash Management page, expand the relevant section, find the record, and click "Restore".' },
  ]

  return (
    <div className="max-w-3xl">
      <header className="mb-8">
        <h2 className="font-headline-lg text-display-md text-primary mb-1">Support</h2>
        <p className="text-on-surface-variant font-body-md">Frequently asked questions and contact information.</p>
      </header>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-6">Frequently Asked Questions</h4>
        <div className="space-y-4">
          {faqs.map((faq, i) => (
            <details key={i} className="group border border-outline-variant rounded-lg overflow-hidden">
              <summary className="flex items-center justify-between px-4 py-3 cursor-pointer bg-surface-container hover:bg-surface-container-high transition-colors">
                <span className="font-body-md font-medium text-on-surface">{faq.q}</span>
                <span className="material-symbols-outlined text-on-surface-variant group-open:rotate-180 transition-transform">expand_more</span>
              </summary>
              <div className="px-4 py-3 bg-surface-container-lowest">
                <p className="text-body-md text-on-surface-variant">{faq.a}</p>
              </div>
            </details>
          ))}
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
        <h4 className="font-headline-sm text-headline-sm text-on-surface mb-4">Contact</h4>
        <p className="text-body-md text-on-surface-variant mb-4">
          Need additional help? Reach out to the Zao support team.
        </p>
        <div className="flex gap-4">
          <a href="mailto:support@zao.ag" className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg text-label-md font-bold hover:bg-primary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]">mail</span>
            Email Support
          </a>
          <button disabled className="flex items-center gap-2 px-4 py-2 border border-outline-variant text-on-surface-variant/40 rounded-lg text-label-md font-bold cursor-not-allowed">
            <span className="material-symbols-outlined text-[16px]">description</span>
            View Docs
          </button>
        </div>
      </div>
    </div>
  )
}

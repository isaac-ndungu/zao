import {
  HiOutlineQrCode,
  HiOutlineCheckCircle,
  HiOutlineCpuChip,
  HiOutlineShieldCheck,
  HiOutlineBanknotes,
  HiOutlineDocumentText,
  HiOutlineCurrencyDollar,
  HiOutlineBuildingLibrary,
  HiOutlineUsers,
  HiOutlineArchiveBox,
  HiOutlineTableCells,
  HiOutlineArrowRight,
} from 'react-icons/hi2'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function Solutions() {
  return (
    <div className="bg-background min-h-screen">
      <Navbar activeLink="/solutions" />

      <main className="max-w-7xl mx-auto px-container-margin py-stack-lg space-y-24">
        <section className="mt-12 text-center space-y-stack-md">
          <span className="text-primary font-label-md text-label-md uppercase tracking-widest bg-secondary-container px-3 py-1 rounded-full inline-block">
            The Modern Pipeline
          </span>
          <h1 className="font-display-lg text-display-lg text-on-surface">The Farm-to-Payout Infrastructure</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            Transforming agricultural logistics into a seamless digital stream. Zao connects the soil to the smartphone with high-precision grading and instant liquidity.
          </p>
        </section>

        <section className="hidden lg:flex justify-between items-center px-12 py-8 bg-surface-container-low rounded-xl border-subtle">
          {['The Gate', 'The Engine', 'The Payout', 'Operations'].map((step, i) => (
            <div key={step} className={`flex flex-col items-center space-y-2 text-center ${i === 0 ? 'group cursor-pointer' : 'opacity-50'}`}>
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  i === 0 ? 'bg-primary text-on-primary' : 'bg-surface-container-highest text-on-surface'
                }`}
              >
                {i === 0 && <HiOutlineQrCode className="w-6 h-6" />}
                {i === 1 && <HiOutlineCpuChip className="w-6 h-6" />}
                {i === 2 && <HiOutlineBanknotes className="w-6 h-6" />}
                {i === 3 && <HiOutlineTableCells className="w-6 h-6" />}
              </div>
              <span className={`font-label-md text-label-md ${i === 0 ? 'text-primary' : ''}`}>{step}</span>
            </div>
          ))}
        </section>

        <section className="bento-grid">
          <div className="col-span-12 md:col-span-5 space-y-stack-md flex flex-col justify-center">
            <div className="flex items-center gap-2 text-primary">
              <HiOutlineQrCode className="w-6 h-6" />
              <h2 className="font-headline-lg text-headline-lg">01. The Gate</h2>
            </div>
            <h3 className="font-headline-sm text-headline-sm">Precision Weighing &amp; Grading</h3>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Zao starts at the collection point. Our mobile-first grading system ensures that every cherry and bean is accounted for with cryptographic integrity. No manual ledgers, no human error.
            </p>
            <ul className="space-y-stack-sm font-body-md text-body-md">
              {[
                'Weight and quality recorded digitally at the collection point.',
                'Standardized grade definitions with rejection reasons and photo evidence.',
                'Grade dispute resolution — farmers can challenge grades, managers resolve with full audit history.',
                'Offline-first syncing for remote collection sites.',
              ].map((text) => (
                <li key={text} className="flex items-start gap-2">
                  <HiOutlineCheckCircle className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <span>{text}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="col-span-12 md:col-span-7 h-[400px] rounded-xl overflow-hidden shadow-sm border-subtle">
            <img
              className="w-full h-full object-cover"
              alt="Hands sorting coffee beans"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuC_whPTjRAiMBoAbnk84ySVFOZTmZIRUY70vBPRrEFs3lQhxHBSQU4bJiUBLyM6X6FF7tlkIQamR3jE2P5TxCfHlYKX6lLzqKbZvHm034Qds_gEKayAIH3kZKHXqzpY0wtqVzXRmwBlBPdRdz850lzZ-e3-Rj7m2m-WpE6AyiRfPXjtrQuYPOAgZUkMFbppHzMzj59MVf0xdy7ww_sC0Oj4vIUbvkZHtSyw1SVc_biOYRP3-UiXBKY4ZKa1G82Yc_4IUCGXopeJZh0"
            />
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-stack-lg items-center bg-surface-container rounded-xl p-stack-lg border-subtle">
          <div className="order-2 md:order-1 bg-surface-container-lowest p-stack-md rounded-lg shadow-sm border border-outline-variant space-y-stack-md">
            <div className="flex justify-between items-center border-b border-outline-variant pb-2">
              <span className="font-label-md text-label-md text-on-surface-variant">Payment Lifecycle</span>
              <span className="font-data-mono-sm text-data-mono-sm text-primary">LOCKED &amp; AUDITED</span>
            </div>
            <div className="space-y-stack-xs">
              {[
                { label: '1. Draft', desc: 'Grades are reviewed before computation begins' },
                { label: '2. Computing', desc: 'Engine calculates payouts from grades, rates, and deductions' },
                { label: '3. Computed', desc: 'Payouts are ready for manager review and approval' },
                { label: '4. Locked', desc: 'Approved payouts are frozen — no further edits allowed' },
                { label: '5. Disbursed', desc: 'Payments sent via M-Pesa, bank transfer, or cash' },
              ].map((row) => (
                <div key={row.label} className="flex justify-between text-body-md font-body-md py-1 border-b border-surface">
                  <span className="text-on-surface-variant">{row.label}</span>
                  <span className="text-on-surface font-medium">{row.desc}</span>
                </div>
              ))}
            </div>
            <div className="bg-secondary-container p-stack-sm rounded border border-secondary text-on-secondary-container text-body-md">
              <div className="flex items-center gap-2">
                <HiOutlineShieldCheck className="w-[18px] h-[18px]" />
                <span>Every step logged immutably to the audit trail</span>
              </div>
            </div>
          </div>
          <div className="order-1 md:order-2 space-y-stack-md">
            <div className="flex items-center gap-2 text-primary">
              <HiOutlineCpuChip className="w-6 h-6" />
              <h2 className="font-headline-lg text-headline-lg">02. The Engine</h2>
            </div>
            <h3 className="font-headline-sm text-headline-sm">Automated Computation</h3>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Our backend engine eliminates the &ldquo;waiting period&rdquo; for farmers. As soon as grading is completed, Zao calculates payouts based on cooperative rates, predefined deductions, and the revenue-share or fixed-price model for each produce type.
            </p>
            <div className="flex items-start gap-3 p-4 bg-white/40 rounded-lg border-subtle">
              <HiOutlineShieldCheck className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-label-md text-label-md font-bold text-primary">Grade Overrides with Audit Trail</p>
                <p className="font-body-md text-body-md text-on-surface-variant">Manager adjustments require a reason and are logged with actor, timestamp, and before/after values.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="bento-grid">
          <div className="col-span-12 md:col-span-6 space-y-stack-md">
            <div className="flex items-center gap-2 text-primary">
              <HiOutlineBuildingLibrary className="w-6 h-6" />
              <h2 className="font-headline-lg text-headline-lg">03. The Payout</h2>
            </div>
            <h3 className="font-headline-sm text-headline-sm">Disbursements at the Right Time</h3>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Liquidity is the lifeblood of farming. Zao integrates directly with M-Pesa and major regional banks to provide instant or scheduled disbursements. No more checks waiting in drawers.
            </p>
            <div className="flex flex-wrap gap-stack-md pt-4">
              <div className="flex items-center gap-3 px-stack-md py-3 bg-surface-container-highest rounded-xl border border-outline-variant w-full sm:w-auto">
                <div className="w-10 h-10 bg-[#34B43C] rounded flex items-center justify-center font-bold text-white text-sm">
                  M
                </div>
                <div>
                  <p className="font-label-md text-label-md font-bold">M-Pesa Integration</p>
                  <p className="font-data-mono-sm text-data-mono-sm">Instant Mobile Transfer</p>
                </div>
              </div>
              <div className="flex items-center gap-3 px-stack-md py-3 bg-surface-container-highest rounded-xl border border-outline-variant w-full sm:w-auto">
                <div className="w-10 h-10 bg-primary rounded flex items-center justify-center text-white">
                  <HiOutlineBuildingLibrary className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-label-md text-label-md font-bold">Bank Disbursement</p>
                  <p className="font-data-mono-sm text-data-mono-sm">EFT &amp; RTGS Ready</p>
                </div>
              </div>
            </div>
          </div>
          <div className="col-span-12 md:col-span-6 grid grid-cols-2 gap-stack-md">
            <div className="col-span-2 sm:col-span-1 bg-primary text-on-primary p-stack-md rounded-xl space-y-4">
              <HiOutlineDocumentText className="w-10 h-10" />
              <h4 className="font-headline-sm text-headline-sm leading-tight">Digital Receipts</h4>
              <p className="font-body-md text-body-md opacity-80">Farmers receive SMS alerts with detailed breakdown of every cent earned.</p>
            </div>
            <div className="col-span-2 sm:col-span-1 bg-surface-container-high p-stack-md rounded-xl space-y-4 border-subtle">
              <HiOutlineCurrencyDollar className="w-10 h-10 text-tertiary" />
              <h4 className="font-headline-sm text-headline-sm leading-tight">Loan Offsets</h4>
              <p className="font-body-md text-body-md text-on-surface-variant">Automated deduction of input loans, fertilizer credits, and member fees.</p>
            </div>
          </div>
        </section>

        <section className="space-y-stack-lg">
          <div className="text-center max-w-3xl mx-auto space-y-stack-md">
            <div className="flex justify-center items-center gap-2 text-primary">
              <HiOutlineTableCells className="w-6 h-6" />
              <h2 className="font-headline-lg text-headline-lg">Cooperative Operations</h2>
            </div>
            <p className="font-body-lg text-body-lg text-on-surface-variant">
              While the data flows from the field, your central office remains in total control. Our dashboard gives managers a bird's-eye view of inventory, finance, and farmer performance.
            </p>
          </div>
          <div className="relative w-full aspect-video rounded-2xl overflow-hidden shadow-lg border-subtle group">
            <img
              className="w-full h-full object-cover"
              alt="Modern cooperative office"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDSfIXWYwbubxxfzdAbtv23xvt3uZ_s08HcQ2f-gCln6hwRnvpc2dNWxkcpo-FZNyORqQHF_SXtjlEDCpxmYuc8SwZSBAIeE110dHO9pPvIns-_AK9wlpEOTY2_gKdmtWEeK-UYraWPCeJqT_F_W2f1ddLbtzL103OzTuCWmBrXINEOZkdLV6PrT1poXCri9fGiVa-3OZ8dcBSeEdBJiJl_uNgaUcgQc_LKINOcKvoqnTpn3xqEpFIoMN8jEnTVmSZBkpSL_Anuwuk"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 flex flex-col justify-end p-stack-lg">
              <div className="glass-card p-stack-md rounded-xl max-w-sm">
                <p className="font-headline-sm text-headline-sm text-primary">Central Command</p>
                <p className="font-body-md text-body-md text-on-surface-variant">A unified system for all cooperative departments.</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-md">
            {[
              { icon: HiOutlineUsers, title: 'Member Management', desc: 'Full digital profiles for every farmer, tracking production over decades.' },
              { icon: HiOutlineArchiveBox, title: 'Stock Control', desc: 'Real-time inventory levels across multiple warehouses and processing zones.' },
              { icon: HiOutlineDocumentText, title: 'Compliance Reporting', desc: 'Automated regulatory and audit reports for government and fair-trade bodies.' },
            ].map((item) => (
              <div key={item.title} className="p-stack-md bg-surface-container-low border-subtle rounded-xl flex items-start gap-stack-md">
                <div className="w-10 h-10 rounded bg-primary-container flex-shrink-0 flex items-center justify-center text-on-primary-container">
                  <item.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-headline-sm text-headline-sm text-on-surface">{item.title}</p>
                  <p className="font-body-md text-body-md text-on-surface-variant">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="py-12 border-t border-outline-variant flex flex-col items-center text-center space-y-stack-md">
          <h2 className="font-display-md text-display-md">Ready to modernize your cooperative?</h2>
          <div className="flex gap-4">
            <button className="bg-primary text-on-primary px-stack-lg py-stack-md rounded-xl font-headline-sm text-headline-sm hover:opacity-90 transition-opacity">
              Request Demo
            </button>
            <button className="border border-primary text-primary px-stack-lg py-stack-md rounded-xl font-headline-sm text-headline-sm hover:bg-primary-container/20 transition-colors">
              Contact Sales
            </button>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}

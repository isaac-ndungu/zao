import {
  HiOutlineArrowTrendingUp,
  HiOutlineHandRaised,
  HiOutlineBuildingLibrary,
  HiOutlineShieldCheck,
  HiOutlineCpuChip,
  HiOutlineCommandLine,
  HiOutlineDocumentText,
  HiOutlineChartBarSquare,
} from 'react-icons/hi2'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

const METRICS = [
  { label: 'Farmers Paid', value: 'Hundreds of thousands', icon: HiOutlineArrowTrendingUp },
  { label: 'Cooperatives Served', value: '480', icon: HiOutlineHandRaised, sub: 'Across 12 Counties' },
  { label: 'Annual GTV', value: 'KSh 42B', icon: HiOutlineBuildingLibrary, sub: 'Processed Securely' },
  { label: 'Audit Trail', value: '100%', icon: HiOutlineShieldCheck, sub: 'Immutable Records' },
]

export default function About() {
  return (
    <div className="bg-background text-on-background min-h-screen">
      <Navbar activeLink="/about" />

      <main>
        <section className="relative h-[80vh] flex items-center overflow-hidden">
          <div className="absolute inset-0 z-0">
            <img
              alt="Aerial view of lush green coffee plantations in the Central Rift Valley of Kenya"
              className="w-full h-full object-cover"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDwijp4O2J_We2JK0LnqjhG7-C5ZkZNaM3Uaaxr92XEVbwlwm_PJqcUFfIQ8vzUU1RIcyFBvpCnGaLrGf7PRCAseBfAZ4N_SyN1rJeu8kq3XxuJCKNf36YSeYKQpxzIxcYUgqEOAaTJ0H5FZZdb-ZWuJutN2KiRDmels0l_U-7gikvl3oYxRDpXKBrSiKYd0qwbhYtg3JucPVH3cq_CkM5T_fRSXswMXXBfkccUghE46XtXAlBjSvaiqWxISuexqBdg_HioRAVg7Vg"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-background via-background/40 to-transparent" />
          </div>
          <div className="relative z-10 w-full max-w-7xl mx-auto px-container-margin">
            <div className="max-w-2xl">
              <span className="text-primary font-bold tracking-widest text-label-md uppercase mb-stack-sm block">Our Roots</span>
              <h1 className="font-display-lg text-display-lg text-primary leading-tight mb-stack-md">
                To modernize the backbone of Kenya&rsquo;s economy.
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant mb-stack-lg leading-relaxed">
                Born in the fertile soils of the Central Rift, Zao was founded to bridge the gap between traditional agricultural cooperatives and the digital age. We provide the analytical precision required to turn smallholder farming into a high-performance business.
              </p>
              <div className="flex gap-stack-md">
                <button className="bg-primary text-on-primary px-6 py-3 rounded text-body-md font-medium">Join our mission</button>
                <button className="border border-primary text-primary px-6 py-3 rounded text-body-md font-medium">View Impact Report</button>
              </div>
            </div>
          </div>
        </section>

        <section className="py-24 bg-surface-container-low">
          <div className="max-w-7xl mx-auto px-container-margin">
            <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-stack-lg">
              <div className="max-w-xl">
                <h2 className="font-headline-lg text-headline-lg text-primary mb-stack-sm">Our Impact</h2>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  Tangible results driving rural prosperity through data-driven cooperative management.
                </p>
              </div>
              <div className="text-right">
                <p className="font-data-mono text-data-mono text-primary font-bold">LATEST UPDATE: NOV 2024</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {METRICS.map((m) => (
                <div key={m.label} className="bg-white border border-[#D8F3DC] p-8 hover:shadow-md transition-shadow">
                  <p className="text-label-md font-label-md text-on-surface-variant uppercase tracking-wider mb-stack-xs">
                    {m.label}
                  </p>
                  <p className="font-display-md text-display-md text-primary mb-stack-sm">{m.value}</p>
                  {m.sub && (
                    <div className="flex items-center gap-1 text-primary">
                      <m.icon className="w-4 h-4" />
                      <span className="font-data-mono-sm text-data-mono-sm">{m.sub}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-24">
          <div className="max-w-7xl mx-auto px-container-margin">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              <div className="lg:col-span-5">
                <h2 className="font-headline-lg text-headline-lg text-primary mb-stack-md leading-tight">
                  Technology &amp; Trust: The New Standard
                </h2>
                <p className="font-body-md text-body-md text-on-surface-variant mb-stack-lg">
                  Agriculture is personal, but management must be precise. We deploy military-grade security protocols to protect farmer livelihoods and cooperative data integrity.
                </p>
                <div className="space-y-6">
                  <div className="flex items-start gap-4">
                    <div className="bg-secondary-container text-secondary p-2 rounded">
                      <HiOutlineShieldCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-headline-sm text-headline-sm text-primary mb-1">Bank-Grade Security</h4>
                      <p className="font-body-md text-body-md text-on-surface-variant">
                        2FA, end-to-end encryption, and real-time audit logs for every transaction.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                    <div className="bg-secondary-container text-secondary p-2 rounded">
                      <HiOutlineCpuChip className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-headline-sm text-headline-sm text-primary mb-1">Offline Resilience</h4>
                      <p className="font-body-md text-body-md text-on-surface-variant">
                        Designed for the reality of rural connectivity—data syncs instantly when back in range.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="lg:col-span-7">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-surface-container-high rounded-xl p-6 flex flex-col justify-between h-48 group hover:bg-primary hover:text-white transition-all">
                    <HiOutlineShieldCheck className="w-8 h-8 mb-4" />
                    <p className="font-body-md font-bold">Immutable Audit Trail</p>
                  </div>
                  <div className="bg-white border border-[#D8F3DC] rounded-xl p-6 flex flex-col justify-between h-64 mt-8">
                    <div className="w-full bg-surface-container-lowest h-1 mb-4 rounded-full overflow-hidden">
                      <div className="bg-primary h-full w-full" />
                    </div>
                    <p className="font-data-mono text-data-mono text-primary">ROLE-BASED ACCESS (6 ROLES)</p>
                    <p className="font-body-md text-on-surface-variant mt-2">
                      Granular permissions for Farmer, Grader, Accountant, Manager, Admin, and Auditor.
                    </p>
                  </div>
                  <div className="bg-primary text-white rounded-xl p-6 flex flex-col justify-between h-64 -mt-8">
                    <HiOutlineCommandLine className="w-8 h-8 mb-4" />
                    <h5 className="font-headline-sm">Open API</h5>
                    <p className="font-body-md opacity-80">
                      Seamlessly integrate with national agricultural registries and financial institutions.
                    </p>
                  </div>
                  <div className="bg-surface-container-highest rounded-xl p-6 flex flex-col justify-between h-48">
                    <HiOutlineDocumentText className="w-8 h-8 mb-4" />
                    <p className="font-body-md font-bold text-primary">KRA-Compliant Reporting</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-24 bg-surface-container-highest">
          <div className="max-w-7xl mx-auto px-container-margin">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl h-[500px]">
                <img
                  className="w-full h-full object-cover"
                  alt="Hand sorting green coffee beans"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuATCDs6jDTFnW9DVPK6Mr_Ke1OspoaJ0dX-fHozj66ySw0ch-F9KjtB3C11f_DosnlvUbvjHon029XfWrsapU7YL3EH8VoI5SLBeoeavRhaAYS3P8YcY1TO-71GbHQUkoANGfCKmzkrDmzAgAGMyW5cY_4mqusGRk0sMn5_SdMBLAwyrS1XvRLGw1EtYxdtzAj2e3lzkBfbPF5-XNRqiGSHXFH6k3NBPQn91c7n3TGR6UPbZx1b7lNRc48Qd8tFfQcbYjMXTDF_ygg"
                />
                <div className="absolute bottom-8 left-8 right-8 glass-card p-6 rounded-lg">
                  <p className="font-data-mono text-data-mono text-primary mb-2">FIELD LOG: ELDORET HUB</p>
                  <p className="font-body-md text-on-surface italic">
                    &ldquo;The transparency we've gained through Zao has returned trust to the cooperative board meetings.&rdquo;
                  </p>
                </div>
              </div>
              <div>
                <h2 className="font-headline-lg text-headline-lg text-primary mb-stack-md">From the Central Rift to the World</h2>
                <div className="space-y-6 font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                  <p>
                    Zao began as a pilot program in Uasin Gishu, tackling the complex logistics of dairy collection. We saw firsthand how manual ledgers led to errors, delays, and an erosion of trust between farmers and their unions.
                  </p>
                  <p>
                    Today, we are a Pan-African team headquartered in Nairobi, with field offices in every major agricultural hub. We don't just build software; we build the infrastructure for the next century of African farming.
                  </p>
                </div>
                <div className="mt-12 flex flex-wrap gap-12">
                  <div>
                    <p className="font-data-mono text-primary text-headline-sm">99.9%</p>
                    <p className="text-label-md uppercase tracking-widest text-on-surface-variant">Data Integrity</p>
                  </div>
                  <div>
                    <p className="font-data-mono text-primary text-headline-sm">KRA</p>
                    <p className="text-label-md uppercase tracking-widest text-on-surface-variant">Tax Compliant</p>
                  </div>
                  <div>
                    <p className="font-data-mono text-primary text-headline-sm">6</p>
                    <p className="text-label-md uppercase tracking-widest text-on-surface-variant">Roles</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-24">
          <div className="max-w-4xl mx-auto px-container-margin text-center">
            <h2 className="font-display-md text-display-md text-primary mb-stack-md">Ready to modernize your cooperative?</h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant mb-stack-lg">
              Join the hundreds of cooperatives already using Zao to increase efficiency and farmer satisfaction.
            </p>
            <div className="flex justify-center gap-4">
              <button className="bg-primary text-on-primary px-10 py-4 rounded font-bold text-body-lg">Get Started</button>
              <button className="border-2 border-primary text-primary px-10 py-4 rounded font-bold text-body-lg">
                Speak to an Expert
              </button>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}

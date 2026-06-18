import { Link } from 'react-router-dom'
import {
  HiOutlineUsers,
  HiOutlineBanknotes,
  HiOutlineArrowPath,
  HiOutlineArrowTrendingUp,
  HiOutlineCheckCircle,
  HiOutlineStar,
  HiOutlineChartBarSquare,
  HiOutlineBolt,
  HiOutlineBuildingLibrary,
  HiOutlineArrowRight,
  HiOutlineDevicePhoneMobile,
  HiOutlineWifi,
} from 'react-icons/hi2'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

const KPIS = [
  {
    label: 'Active Farmers',
    value: '12,482',
    icon: HiOutlineUsers,
    trend: '+14% this month',
    trendIcon: HiOutlineArrowTrendingUp,
    trendColor: 'text-secondary',
  },
  {
    label: 'Payments Processed',
    value: 'KES 42.8M',
    icon: HiOutlineBanknotes,
    note: 'Real-time settlement',
    noteIcon: HiOutlineCheckCircle,
  },
  {
    label: 'Produce Graded',
    value: '850 Tons',
    icon: HiOutlineArrowPath,
    note: '98% Grade A quality',
    noteIcon: HiOutlineStar,
  },
]

const FEATURES = [
  {
    icon: HiOutlineChartBarSquare,
    iconBg: 'bg-primary-container',
    iconColor: 'text-on-primary-container',
    title: 'Digital Grading',
    desc: 'Eliminate disputes with objective digital grading. Ensure farmers receive exactly what their produce is worth based on standardized quality definitions.',
  },
  {
    icon: HiOutlineBolt,
    iconBg: 'bg-secondary',
    iconColor: 'text-white',
    title: 'Automated Payment Cycles',
    desc: 'Payments flow through a locked, auditable lifecycle — computed, approved, and disbursed on your cooperative\'s schedule. No more waiting weeks for harvest proceeds.',
    highlighted: true,
  },
  {
    icon:   HiOutlineBuildingLibrary,
    iconBg: 'bg-tertiary-container',
    iconColor: 'text-on-tertiary-container',
    title: 'Farmer Loans',
    desc: 'Integrated credit scoring based on delivery history. Provide input financing and emergency loans directly through the Zao ecosystem.',
  },
  {
    icon: HiOutlineDevicePhoneMobile,
    iconBg: 'bg-secondary-container',
    iconColor: 'text-secondary',
    title: 'USSD Self-Service',
    desc: 'Farmers check balances, delivery history, and payment status on any phone via *384*ZAO#. No smartphone or data plan required.',
  },
  {
    icon: HiOutlineWifi,
    iconBg: 'bg-tertiary-container',
    iconColor: 'text-on-tertiary-container',
    title: 'Offline-First Grading',
    desc: 'Graders record produce at rural collection points with zero connectivity. Data syncs automatically when back online. Built for low-connectivity environments.',
  },
]

export default function Home() {
  return (
    <div className="bg-background min-h-screen">
      <Navbar activeLink="/" />

      <main>
        <section className="relative min-h-[85vh] flex items-center justify-center text-center px-container-margin overflow-hidden">
          <div
            className="absolute inset-0 hero-gradient"
            style={{
              backgroundImage:
                'linear-gradient(to bottom, rgba(15, 82, 56, 0.4), rgba(12, 32, 18, 0.9)), url(https://lh3.googleusercontent.com/aida-public/AB6AXuDwijp4O2J_We2JK0LnqjhG7-C5ZkZNaM3Uaaxr92XEVbwlwm_PJqcUFfIQ8vzUU1RIcyFBvpCnGaLrGf7PRCAseBfAZ4N_SyN1rJeu8kq3XxuJCKNf36YSeYKQpxzIxcYUgqEOAaTJ0H5FZZdb-ZWuJutN2KiRDmels0l_U-7gikvl3oYxRDpXKBrSiKYd0qwbhYtg3JucPVH3cq_CkM5T_fRSXswMXXBfkccUghE46XtXAlBjSvaiqWxISuexqBdg_HioRAVg7Vg)',
            }}
          />
          <div className="max-w-4xl relative z-10">
            <span className="inline-block px-stack-sm py-1 mb-stack-md rounded-full bg-secondary-container text-on-secondary-container font-label-md text-label-md uppercase tracking-wider">
              Next-Gen Agri-Tech
            </span>
            <h1 className="font-display-lg text-display-lg md:text-8xl text-white mb-stack-md leading-tight">
              Empowering Cooperatives, <br />
              <span className="italic text-secondary-fixed">Elevating Farmers</span>
            </h1>
            <p className="font-body-lg text-body-lg text-surface-variant mb-stack-lg max-w-2xl mx-auto opacity-90">
              Modernize your agricultural supply chain with real-time data, instant payments, and precise digital grading. Built for the future of Kenya's cooperatives.
            </p>
            <div className="flex flex-col md:flex-row gap-stack-md justify-center items-center">
              <button className="w-full md:w-auto px-10 py-4 bg-tertiary-fixed-dim text-on-tertiary-fixed font-bold rounded-xl text-body-lg active:scale-95 transition-all shadow-xl hover:shadow-2xl">
                Request Demo
              </button>
              <button className="w-full md:w-auto px-10 py-4 border-2 border-white/30 text-white font-bold rounded-xl text-body-lg hover:bg-white/10 active:scale-95 transition-all">
                Learn More
              </button>
            </div>
          </div>
        </section>

        <section className="py-stack-lg px-container-margin max-w-7xl mx-auto -mt-24 relative z-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-md">
            {KPIS.map((kpi) => (
              <div key={kpi.label} className="glass-card p-stack-lg rounded-xl shadow-sm">
                <div className="flex items-center justify-between mb-stack-sm">
                  <span className="font-label-md text-label-md text-on-surface-variant uppercase">{kpi.label}</span>
                  <kpi.icon className="w-6 h-6 text-primary" />
                </div>
                <div className="font-display-md text-display-md text-primary">{kpi.value}</div>
                <div className="flex items-center gap-1 mt-stack-xs">
                  {kpi.trendIcon && <kpi.trendIcon className={`w-4 h-4 ${kpi.trendColor || 'text-secondary'}`} />}
                  {kpi.noteIcon && <kpi.noteIcon className="w-4 h-4 text-secondary" />}
                  <span className={`font-data-mono-sm text-data-mono-sm ${kpi.trendColor || 'text-on-surface-variant'}`}>
                    {kpi.trend || kpi.note}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="py-stack-lg px-container-margin max-w-7xl mx-auto">
          <div className="text-center mb-stack-lg">
            <h2 className="font-headline-lg text-headline-lg text-primary mb-2">Designed for the Modern Cooperative</h2>
            <p className="text-on-surface-variant font-body-md text-body-md max-w-xl mx-auto">
              Our platform bridges the gap between traditional farming and digital financial precision.
            </p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-stack-lg items-center">
            <div className="order-2 lg:order-1 space-y-stack-md">
              {FEATURES.map((f) => (
                <div
                  key={f.title}
                  className={`flex gap-stack-md p-stack-md rounded-xl transition-colors group ${
                    f.highlighted ? 'bg-surface-container-high shadow-sm border border-outline-variant' : 'hover:bg-surface-container-low'
                  }`}
                >
                  <div
                    className={`flex-shrink-0 w-12 h-12 ${f.iconBg} rounded-lg flex items-center justify-center ${f.iconColor}`}
                  >
                    <f.icon className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-headline-sm text-headline-sm text-primary mb-1">{f.title}</h3>
                    <p className="font-body-md text-body-md text-on-surface-variant">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="order-1 lg:order-2">
              <div className="relative rounded-2xl overflow-hidden shadow-2xl border-4 border-white">
                <img
                  className="w-full h-[500px] object-cover"
                  alt="Terraced coffee and tea plantation in the Kenyan Highlands"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuDwijp4O2J_We2JK0LnqjhG7-C5ZkZNaM3Uaaxr92XEVbwlwm_PJqcUFfIQ8vzUU1RIcyFBvpCnGaLrGf7PRCAseBfAZ4N_SyN1rJeu8kq3XxuJCKNf36YSeYKQpxzIxcYUgqEOAaTJ0H5FZZdb-ZWuJutN2KiRDmels0l_U-7gikvl3oYxRDpXKBrSiKYd0qwbhYtg3JucPVH3cq_CkM5T_fRSXswMXXBfkccUghE46XtXAlBjSvaiqWxISuexqBdg_HioRAVg7Vg"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/60 to-transparent flex items-end p-stack-lg">
                  <div className="bg-white/90 backdrop-blur p-stack-md rounded-xl max-w-xs shadow-xl">
                    <p className="font-body-md text-body-md text-primary font-bold italic">
                      &ldquo;Zao transformed our coffee cooperative from paper ledgers to a 100% digital operation in just 30 days.&rdquo;
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-surface-container-lowest py-stack-lg px-container-margin">
          <div className="max-w-7xl mx-auto bg-primary rounded-[2rem] overflow-hidden flex flex-col md:flex-row shadow-2xl">
            <div className="md:w-1/2 h-[400px] md:h-auto overflow-hidden">
              <img
                className="w-full h-full object-cover"
                alt="Kenyan farmer with tablet"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBIjhoCVtedmXupuPZX32Gtlx4WrDlCxhSCfey3bNal1VNk-iwXs8Vt6t3accaIg8ieozij83-2FY1SGpNQqSQIa-DJD6QC1r2HStvv2nohZLaSPK1VnRpw-3nmn_fjSPVYJtlgtdJ0h6IvyAdb5ahqnlJ_JjE7_NW7qaYtnMQ02VNwtQ4lTacWyDvhp5hHn0qIdnA176u6ME9y8RRJQB0sTOArhznt3b6c0RLzFF5CpS3QfWNTa4tsXLJmdxNgTVNalupic8vzmnM"
              />
            </div>
            <div className="md:w-1/2 p-stack-lg md:p-16 flex flex-col justify-center text-white">
              <HiOutlineChartBarSquare className="w-16 h-16 text-tertiary-fixed mb-stack-md" />
              <h2 className="font-display-md text-display-md mb-stack-md">
                &ldquo;Since joining the Zao network, my income is visible and my payments are certain. I can finally plan for my family's
                future.&rdquo;
              </h2>
              <div className="flex items-center gap-stack-md">
                <div className="h-px w-12 bg-secondary-fixed" />
                <div>
                  <p className="font-headline-sm text-headline-sm">Samuel Mwangi</p>
                  <p className="font-body-md text-body-md text-secondary-fixed">Smallholder Coffee Farmer, Nyeri County</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="py-24 text-center px-container-margin bg-surface-bright">
          <div className="max-w-3xl mx-auto">
            <h2 className="font-display-lg text-display-lg text-primary mb-stack-md">Ready to modernize your operations?</h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant mb-stack-lg">
              Join hundreds of cooperatives across East Africa leveraging Zao to increase efficiency and farmer loyalty.
            </p>
            <div className="flex flex-col sm:flex-row gap-stack-md justify-center">
              <button className="px-12 py-5 bg-primary text-on-primary font-bold rounded-xl text-body-lg active:scale-95 transition-all shadow-lg hover:shadow-xl">
                Schedule a Demo
              </button>
              <Link
                to="/about"
                className="px-12 py-5 border-2 border-primary text-primary font-bold rounded-xl text-body-lg active:scale-95 transition-all hover:bg-primary/5 inline-block"
              >
                Contact Sales
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}

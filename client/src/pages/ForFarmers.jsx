import {
  HiOutlineDevicePhoneMobile,
  HiOutlineCheckCircle,
  HiOutlineBanknotes,
  HiOutlineBuildingLibrary,
  HiOutlineShieldCheck,
  HiOutlineRocketLaunch,
  HiOutlineArrowRight,
} from 'react-icons/hi2'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function ForFarmers() {
  return (
    <div className="bg-background min-h-screen overflow-x-hidden">
      <Navbar activeLink="/farmers" />

      <section className="relative min-h-[80vh] flex flex-col justify-end">
        <div className="absolute inset-0 z-0 overflow-hidden">
          <img
            alt="Farmer with Tablet"
            className="w-full h-full object-cover object-center"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBIjhoCVtedmXupuPZX32Gtlx4WrDlCxhSCfey3bNal1VNk-iwXs8Vt6t3accaIg8ieozij83-2FY1SGpNQqSQIa-DJD6QC1r2HStvv2nohZLaSPK1VnRpw-3nmn_fjSPVYJtlgtdJ0h6IvyAdb5ahqnlJ_JjE7_NW7qaYtnMQ02VNwtQ4lTacWyDvhp5hHn0qIdnA176u6ME9y8RRJQB0sTOArhznt3b6c0RLzFF5CpS3QfWNTa4tsXLJmdxNgTVNalupic8vzmnM"
          />
          <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(234, 255, 234, 0) 0%, #eaffea 100%)' }} />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto w-full px-container-margin pb-stack-lg">
          <div className="max-w-2xl bg-white/75 backdrop-blur-lg p-8 rounded-3xl border border-white/50 shadow-2xl">
            <span className="text-primary font-label-md text-label-md uppercase tracking-widest mb-stack-xs block">
              Zao Farmer Portal
            </span>
            <h1 className="font-display-lg text-display-lg text-on-surface mb-stack-sm">Transparency in Every Harvest</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant mb-stack-md">
              Empowering modern Kenyan farmers with the digital tools they need to track deliveries, secure fair payments, and grow their agricultural business with confidence.
            </p>
            <div className="flex flex-col sm:flex-row gap-stack-md">
              <Link to="/contact" className="bg-primary text-on-primary px-8 py-4 rounded-lg font-headline-sm text-headline-sm flex items-center justify-center gap-2 hover:bg-primary-container transition-colors shadow-lg active:scale-[0.98]">
                Check via USSD
                <HiOutlineArrowRight className="w-5 h-5" />
              </Link>
              <Link to="/farmer/login" className="border-2 border-primary text-primary px-8 py-4 rounded-lg font-headline-sm text-headline-sm flex items-center justify-center gap-2 hover:bg-surface-container transition-colors active:scale-[0.98]">
                Explore Portal
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="py-stack-lg bg-surface px-container-margin">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 md:row-span-2 glass-panel rounded-xl p-8 flex flex-col md:flex-row items-center gap-8 overflow-hidden">
              <div className="flex-1 space-y-6">
                <div className="p-3 bg-secondary-container rounded-full w-fit">
                  <HiOutlineDevicePhoneMobile className="w-6 h-6 text-secondary" />
                </div>
                <h2 className="font-headline-lg text-headline-lg text-primary">Your Harvest in Your Pocket</h2>
                <p className="font-body-lg text-body-lg text-on-surface-variant">
                  Access your delivery notes, payment status, and agricultural insights from anywhere. Our interface is designed for low-connectivity environments, ensuring you always have your data when you need it.
                </p>
                <ul className="space-y-4">
                  {[
                    'SMS delivery confirmations for every transaction',
                    'Offline mode for remote farm management',
                    '2FA-secured portal for data safety',
                  ].map((text) => (
                    <li key={text} className="flex items-center gap-3 font-body-md text-body-md">
                      <HiOutlineCheckCircle className="w-5 h-5 text-primary flex-shrink-0" />
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative w-64 h-[500px] bg-black rounded-[2.5rem] border-[8px] border-on-surface overflow-hidden shadow-2xl flex-shrink-0">
                <div className="absolute top-0 inset-x-0 h-6 bg-black flex justify-center items-end pb-1">
                  <div className="w-16 h-4 bg-on-surface rounded-full" />
                </div>
                <div className="bg-surface-container-low h-full w-full p-4 pt-8">
                  <div className="flex justify-between items-center mb-4">
                    <div className="text-primary font-bold text-sm">Zao Portal</div>
                    <HiOutlineBanknotes className="w-5 h-5 text-on-surface-variant" />
                  </div>
                  <div className="bg-primary p-3 rounded-lg text-white mb-4">
                      <div className="text-[10px] opacity-80 uppercase tracking-tight">Active Balance</div>
                      <div className="text-xl font-bold font-data-mono">—</div>
                  </div>
                  <div className="space-y-3">
                    <div className="text-[12px] font-bold text-on-surface-variant uppercase">Recent Harvests</div>
                    <div className="text-sm text-on-surface-variant">No recent harvests</div>
                  </div>
                  <div className="mt-4 p-2 bg-tertiary-fixed rounded border border-tertiary/20">
                    <div className="text-[10px] font-bold text-tertiary uppercase">Input Loans</div>
                    <div className="text-[12px] text-on-tertiary-fixed-variant leading-tight">
                      Input loans available through your cooperative. Speak to your manager.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white/70 backdrop-blur-md rounded-2xl p-8 border border-outline-variant/20 shadow-sm group hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <div className="mb-6 h-12 w-12 bg-primary flex items-center justify-center rounded-xl text-on-primary shadow-md shadow-primary/20 transition-transform duration-300 group-hover:scale-110">
                <HiOutlineBanknotes className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Real-time Payment Tracking</h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                No more guessing games. See exactly when your cooperative processes your payments and track them directly to your bank or mobile wallet.
              </p>
            </div>

            <div className="bg-white/70 backdrop-blur-md rounded-2xl p-8 border border-outline-variant/20 shadow-sm group hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <div className="mb-6 h-12 w-12 bg-secondary flex items-center justify-center rounded-xl text-on-secondary shadow-md shadow-secondary/20 transition-transform duration-300 group-hover:scale-110">
                <HiOutlineBuildingLibrary className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Easy Loan Access</h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                Apply for agricultural input loans or emergency credit based on your delivery history. Fast approval, fair rates, no paper stress.
              </p>
            </div>

            <div className="bg-white/70 backdrop-blur-md rounded-2xl p-8 border border-outline-variant/20 shadow-sm group hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <div className="mb-6 h-12 w-12 bg-tertiary flex items-center justify-center rounded-xl text-on-tertiary shadow-md shadow-tertiary/20 transition-transform duration-300 group-hover:scale-110">
                <HiOutlineShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Grade Dispute Resolution</h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                If you disagree with a grade on your delivery, file a dispute through the portal. Managers review with full audit logs for transparent resolution.
              </p>
            </div>

            <div className="md:col-span-3 bg-white/70 backdrop-blur-md rounded-3xl p-8 border border-outline-variant/20 shadow-md flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex-1">
                <h3 className="font-headline-lg text-headline-lg text-primary mb-4">Digital Delivery History</h3>
                <p className="font-body-lg text-body-lg text-on-surface-variant max-w-xl leading-relaxed">
                  A complete, tamper-proof record of every delivery you've ever made. Perfect for business planning and securing financing from external lenders.
                </p>
              </div>
              <div className="flex-1 w-full overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[500px]">
                  <thead>
                    <tr className="bg-primary text-white">
                      <th scope="col" className="p-3 font-label-md text-label-md rounded-tl-xl">DATE</th>
                      <th scope="col" className="p-3 font-label-md text-label-md">PRODUCE</th>
                      <th scope="col" className="p-3 font-label-md text-label-md">QUANTITY</th>
                      <th scope="col" className="p-3 font-label-md text-label-md rounded-tr-xl">STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="font-data-mono-sm text-data-mono-sm">
                    <tr>
                      <td colSpan={4} className="p-3 text-center text-on-surface-variant">No delivery records yet</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-stack-lg bg-primary-container text-on-primary-container relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-container-margin relative z-10 grid md:grid-cols-2 items-center gap-12">
          <div className="space-y-6">
            <h2 className="font-headline-lg text-headline-lg">Bank-Grade Security for Your Hard Work</h2>
            <p className="font-body-lg text-body-lg opacity-90">
              At Zao, we understand that your harvest represents months of labor. That's why our portal uses the same encryption standards as major financial institutions. Every transaction is immutable and verifiable.
            </p>
            <div className="grid grid-cols-2 gap-stack-md pt-stack-sm">
              <div className="flex items-center gap-3">
                <HiOutlineShieldCheck className="w-5 h-5 text-secondary-fixed" />
                <span className="font-label-md text-label-md">Encrypted Data</span>
              </div>
              <div className="flex items-center gap-3">
                <HiOutlineRocketLaunch className="w-5 h-5 text-secondary-fixed" />
                <span className="font-label-md text-label-md">Instant Sync</span>
              </div>
            </div>
          </div>
          <div className="bg-white/15 backdrop-blur-lg p-8 rounded-2xl border border-white/25 text-center shadow-xl">
            <h3 className="font-headline-sm text-headline-sm mb-4">Ready to upgrade your farm management?</h3>
            <p className="font-body-md text-body-md mb-8 opacity-80">
              Contact your cooperative manager today to get your Zao Farmer Portal login credentials.
            </p>
            <div className="flex flex-col gap-4">
              <Link to="/contact" className="bg-surface-bright text-primary px-8 py-4 rounded-lg font-bold hover:bg-white transition-all shadow-lg active:scale-95 text-center">
                Contact Your Cooperative Manager
              </Link>
              <Link to="/about" className="text-white hover:underline font-body-md text-body-md">
                Learn more about Zao security
              </Link>
            </div>
          </div>
        </div>
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-white/5 rounded-full blur-3xl" />
        <div className="absolute -left-20 -bottom-20 w-80 h-80 bg-secondary-fixed/5 rounded-full blur-3xl" />
      </section>

      <Footer />
    </div>
  )
}

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
          <div className="max-w-2xl bg-surface-container-lowest/80 backdrop-blur-md p-stack-lg rounded-xl border border-outline-variant/30">
            <span className="text-primary font-label-md text-label-md uppercase tracking-widest mb-stack-xs block">
              Zao Farmer Portal
            </span>
            <h1 className="font-display-lg text-display-lg text-on-surface mb-stack-sm">Transparency in Every Harvest</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant mb-stack-md">
              Empowering modern Kenyan farmers with the digital tools they need to track deliveries, secure fair payments, and grow their agricultural business with confidence.
            </p>
            <div className="flex flex-col sm:flex-row gap-stack-md">
              <button className="bg-primary text-on-primary px-8 py-4 rounded-lg font-headline-sm text-headline-sm flex items-center justify-center gap-2 hover:bg-primary-container transition-colors shadow-lg active:scale-[0.98]">
                Join Local Cooperative
                <HiOutlineArrowRight className="w-5 h-5" />
              </button>
              <button className="border-2 border-primary text-primary px-8 py-4 rounded-lg font-headline-sm text-headline-sm flex items-center justify-center gap-2 hover:bg-surface-container transition-colors active:scale-[0.98]">
                Explore Portal
              </button>
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
                    'SMS & Push Notifications for every delivery',
                    'Offline mode for remote farm management',
                    'Secure biometric login for data safety',
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
                    <div className="text-xl font-bold font-data-mono">KES 42,850.00</div>
                  </div>
                  <div className="space-y-3">
                    <div className="text-[12px] font-bold text-on-surface-variant uppercase">Recent Harvests</div>
                    {[
                      { produce: 'Coffee (Cherry)', date: 'AUG 14, 2024', qty: '82.5 KG' },
                      { produce: 'Dairy (Morning)', date: 'AUG 13, 2024', qty: '12.0 L' },
                    ].map((h) => (
                      <div key={h.produce} className="bg-white p-2 rounded border border-surface-variant flex justify-between items-center">
                        <div>
                          <div className="text-[12px] font-bold text-on-surface">{h.produce}</div>
                          <div className="text-[10px] text-on-surface-variant font-data-mono">{h.date}</div>
                        </div>
                        <div className="text-[12px] font-bold text-secondary">{h.qty}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 p-2 bg-tertiary-fixed rounded border border-tertiary/20">
                    <div className="text-[10px] font-bold text-tertiary uppercase">Loan Offer</div>
                    <div className="text-[12px] text-on-tertiary-fixed-variant leading-tight">
                      You qualify for an input loan of up to KES 15,000.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-highest rounded-xl p-8 border border-outline-variant/30 group hover:shadow-md transition-all">
              <div className="mb-6 h-12 w-12 bg-primary flex items-center justify-center rounded-lg text-on-primary">
                <HiOutlineBanknotes className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Real-time Payment Tracking</h3>
              <p className="font-body-md text-body-md text-on-surface-variant">
                No more guessing games. See exactly when your cooperative processes your payments and track them directly to your bank or mobile wallet.
              </p>
            </div>

            <div className="bg-surface-container-highest rounded-xl p-8 border border-outline-variant/30 group hover:shadow-md transition-all">
              <div className="mb-6 h-12 w-12 bg-secondary flex items-center justify-center rounded-lg text-on-secondary">
                <HiOutlineBuildingLibrary className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Easy Loan Access</h3>
              <p className="font-body-md text-body-md text-on-surface-variant">
                Apply for agricultural input loans or emergency credit based on your delivery history. Fast approval, fair rates, no paper stress.
              </p>
            </div>

            <div className="md:col-span-3 glass-panel rounded-xl p-8 flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex-1">
                <h3 className="font-headline-lg text-headline-lg text-primary mb-4">Digital Delivery History</h3>
                <p className="font-body-lg text-body-lg text-on-surface-variant max-w-xl">
                  A complete, tamper-proof record of every delivery you've ever made. Perfect for business planning and securing financing from external lenders.
                </p>
              </div>
              <div className="flex-1 w-full overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[500px]">
                  <thead>
                    <tr className="bg-primary text-white">
                      <th className="p-3 font-label-md text-label-md rounded-tl-lg">DATE</th>
                      <th className="p-3 font-label-md text-label-md">PRODUCE</th>
                      <th className="p-3 font-label-md text-label-md">QUANTITY</th>
                      <th className="p-3 font-label-md text-label-md rounded-tr-lg">STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="font-data-mono-sm text-data-mono-sm">
                    {[
                      { date: '2024-08-12', produce: 'Dairy (Morning)', qty: '14.5 L', status: 'VERIFIED' },
                      { date: '2024-08-11', produce: 'Cherry A1', qty: '120.0 KG', status: 'VERIFIED' },
                      { date: '2024-08-10', produce: 'Dairy (Evening)', qty: '8.2 L', status: 'PENDING' },
                    ].map((row, i) => (
                      <tr key={row.date} className={i % 2 === 0 ? 'bg-white border-b border-surface-variant' : 'bg-surface-container-low border-b border-surface-variant'}>
                        <td className="p-3">{row.date}</td>
                        <td className="p-3">{row.produce}</td>
                        <td className="p-3">{row.qty}</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] ${
                              row.status === 'VERIFIED'
                                ? 'bg-secondary-container text-on-secondary-container'
                                : 'bg-tertiary-fixed text-on-tertiary-fixed-variant'
                            }`}
                          >
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
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
          <div className="bg-white/10 backdrop-blur-md p-stack-lg rounded-xl border border-white/20 text-center">
            <h3 className="font-headline-sm text-headline-sm mb-4">Ready to upgrade your farm management?</h3>
            <p className="font-body-md text-body-md mb-8 opacity-80">
              Contact your cooperative manager today to get your Zao Farmer Portal login credentials.
            </p>
            <div className="flex flex-col gap-4">
              <button className="bg-surface-bright text-primary px-8 py-4 rounded-lg font-bold hover:bg-white transition-all shadow-lg active:scale-95">
                Find My Cooperative
              </button>
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

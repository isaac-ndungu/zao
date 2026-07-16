import { useState } from 'react'
import {
  HiOutlineEnvelope,
  HiOutlinePhone,
  HiOutlineMapPin,
  HiOutlineClock,
  HiOutlinePaperAirplane,
  HiOutlineCheckCircle,
} from 'react-icons/hi2'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { useFormAction } from '../shared/hooks/useFormAction'

const CONTACT_INFO = [
  {
    icon: HiOutlineEnvelope,
    label: 'Email',
    value: 'support@zao.ag',
    href: 'mailto:support@zao.ag',
  },
  {
    icon: HiOutlinePhone,
    label: 'Phone',
    value: '+254 700 000 000',
    href: 'tel:+254700000000',
  },
  {
    icon: HiOutlineMapPin,
    label: 'Address',
    value: 'Nairobi, Kenya',
    href: null,
  },
  {
    icon: HiOutlineClock,
    label: 'Office Hours',
    value: 'Mon–Fri, 8:00 AM – 5:00 PM (EAT)',
    href: null,
  },
]

const FAQS = [
  {
    q: 'How do I get started with Zao?',
    a: 'Contact your cooperative manager to request access. They will create your account and provide login credentials for the Farmer Portal.',
  },
  {
    q: 'I forgot my password — what do I do?',
    a: 'Use the "Forgot Password" link on the login page to reset your password via email. Farmers can request a new OTP via SMS.',
  },
  {
    q: 'How long do payments take to process?',
    a: 'Payments are processed in cycles. Once a cycle is computed and approved, disbursements reach farmers within 24–48 hours depending on the payout method.',
  },
  {
    q: 'Can I dispute a grade on my delivery?',
    a: 'Yes. File a dispute through the Farmer Portal. Your cooperative manager will review the grade using the full audit trail.',
  },
]

export default function Contact() {
  const [submitted, setSubmitted] = useState(false)

  const [, contactAction] = useFormAction(async (prev, formData) => {
    const name = formData.get('name')
    const email = formData.get('email')
    const subject = formData.get('subject')
    const message = formData.get('message')
    const mailtoLink = `mailto:support@zao.ag?subject=${encodeURIComponent(`[Zao Contact] ${subject}`)}&body=${encodeURIComponent(`Name: ${name}\nEmail: ${email}\n\n${message}`)}`
    window.location.href = mailtoLink
    setSubmitted(true)
    return { success: true }
  }, {})

  return (
    <div className="bg-background min-h-screen">
      <Navbar activeLink="/contact" />

      <section className="relative min-h-[50vh] flex items-center justify-center text-center px-container-margin overflow-hidden">
        <div className="absolute inset-0 hero-gradient"
          style={{
            backgroundImage:
              'linear-gradient(to bottom, rgba(15, 82, 56, 0.4), rgba(12, 32, 18, 0.9)), url(https://lh3.googleusercontent.com/aida-public/AB6AXuDwijp4O2J_We2JK0LnqjhG7-C5ZkZNaM3Uaaxr92XEVbwlwm_PJqcUFfIQ8vzUU1RIcyFBvpCnGaLrGf7PRCAseBfAZ4N_SyN1rJeu8kq3XxuJCKNf36YSeYKQpxzIxcYUgqEOAaTJ0H5FZZdb-ZWuJutN2KiRDmels0l_U-7gikvl3oYxRDpXKBrSiKYd0qwbhYtg3JucPVH3cq_CkM5T_fRSXswMXXBfkccUghE46XtXAlBjSvaiqWxISuexqBdg_HioRAVg7Vg',
          }}
        />
        <div className="relative z-10 max-w-3xl">
          <span className="inline-block px-stack-sm py-1 mb-stack-md rounded-full bg-secondary-container text-on-secondary-container font-label-md text-label-md uppercase tracking-wider">
            Get in Touch
          </span>
          <h1 className="font-display-lg text-display-lg md:text-7xl text-white mb-stack-md leading-tight">
            We'd Love to Hear From You
          </h1>
          <p className="font-body-lg text-body-lg text-surface-variant max-w-2xl mx-auto opacity-90">
            Have a question about Zao, want to request a demo for your cooperative, or need help with your account? Reach out — our team is ready to help.
          </p>
        </div>
      </section>

      <section className="py-stack-lg px-container-margin max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-6">
            <h2 className="font-headline-lg text-headline-lg text-primary">Contact Information</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Prefer email or phone? Use any of the channels below and we'll get back to you promptly.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {CONTACT_INFO.map((item) => (
                <div key={item.label} className="bg-white/70 backdrop-blur-md rounded-xl p-5 border border-outline-variant/20 shadow-sm group hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
                  <div className="mb-3 w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary transition-transform duration-300 group-hover:scale-110">
                    <item.icon className="w-5 h-5" aria-hidden="true" />
                  </div>
                  <h3 className="font-label-md text-label-md text-on-surface-variant mb-1">{item.label}</h3>
                  {item.href ? (
                    <a href={item.href} className="font-body-md text-body-md text-primary hover:underline">{item.value}</a>
                  ) : (
                    <p className="font-body-md text-body-md text-on-surface">{item.value}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white/70 backdrop-blur-md rounded-2xl p-8 border border-outline-variant/20 shadow-md">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-6">Send Us a Message</h2>
            {submitted ? (
                <div className="text-center py-12">
                  <HiOutlineCheckCircle className="w-16 h-16 text-primary mx-auto mb-4" aria-hidden="true" />
                  <p className="font-headline-sm text-headline-sm text-primary mb-2">Message Ready to Send</p>
                <p className="font-body-md text-body-md text-on-surface-variant mb-6">
                  Your default email client will open with the message pre-filled. Just click send.
                </p>
                <button
                  onClick={() => setSubmitted(false)}
                  className="px-6 py-3 bg-primary text-on-primary rounded-lg font-bold hover:bg-primary/90 transition-colors"
                >
                  Send Another Message
                </button>
              </div>
            ) : (
              <form action={contactAction} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="contact-name" className="block text-label-md font-bold text-on-surface mb-1.5">Your Name *</label>
                    <input
                      id="contact-name"
                      name="name"
                      type="text"
                      required
                      placeholder="John Kamau"
                      className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2.5 text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                    />
                  </div>
                  <div>
                    <label htmlFor="contact-email" className="block text-label-md font-bold text-on-surface mb-1.5">Your Email *</label>
                    <input
                      id="contact-email"
                      name="email"
                      type="email"
                      required
                      placeholder="john@cooperative.co.ke"
                      className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2.5 text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="contact-subject" className="block text-label-md font-bold text-on-surface mb-1.5">Subject *</label>
                  <input
                    id="contact-subject"
                    name="subject"
                    type="text"
                    required
                    placeholder="Demo Request, Support Question, Partnership..."
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2.5 text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                  />
                </div>
                <div>
                  <label htmlFor="contact-message" className="block text-label-md font-bold text-on-surface mb-1.5">Message *</label>
                  <textarea
                    id="contact-message"
                    name="message"
                    required
                    rows={5}
                    placeholder="Tell us how we can help..."
                    className="w-full bg-surface-container border border-outline-variant rounded-lg px-3 py-2.5 text-body-md text-on-surface placeholder:text-on-surface-variant resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary text-on-primary rounded-lg font-bold hover:bg-primary/90 transition-colors active:scale-[0.98]"
                >
                  <HiOutlinePaperAirplane className="w-5 h-5" aria-hidden="true" />
                  Send Message
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      <section className="py-stack-lg bg-surface-bright px-container-margin">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-headline-lg text-headline-lg text-primary text-center mb-stack-md">Frequently Asked Questions</h2>
          <div className="space-y-4">
            {FAQS.map((faq) => (
              <details key={faq.q} className="bg-white/70 backdrop-blur-md rounded-xl border border-outline-variant/20 group open:shadow-md transition-all">
                <summary className="px-6 py-4 font-headline-sm text-headline-sm text-on-surface cursor-pointer hover:text-primary transition-colors flex items-center justify-between list-none">
                  {faq.q}
                  <span className="material-symbols-outlined text-on-surface-variant group-open:rotate-180 transition-transform text-[20px]" aria-hidden="true">expand_more</span>
                </summary>
                <div className="px-6 pb-4">
                  <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">{faq.a}</p>
                </div>
              </details>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

import { HiOutlineGlobeAmericas, HiOutlineAtSymbol } from 'react-icons/hi2'

export default function Footer() {
  return (
    <footer className="bg-surface-container-highest" aria-label="Footer">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-stack-lg w-full px-container-margin py-stack-lg max-w-7xl mx-auto">
        <div className="col-span-2 md:col-span-1">
          <div className="font-headline-sm text-headline-sm font-bold text-primary mb-stack-md">Zao</div>
          <p className="text-on-surface-variant font-body-md text-body-md max-w-xs">
            Precision management for the modern agricultural ecosystem.
          </p>
        </div>
        <div className="flex flex-col gap-stack-sm">
          <h4 className="font-label-md text-label-md uppercase text-primary font-bold">Produce</h4>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/solutions">Coffee</a>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/solutions">Dairy</a>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/solutions">Honey</a>
        </div>
        <div className="flex flex-col gap-stack-sm">
          <h4 className="font-label-md text-label-md uppercase text-primary font-bold">Company</h4>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/about">About Us</a>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/contact">Contact Us</a>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="#">Careers</a>
        </div>
        <div className="flex flex-col gap-stack-sm">
          <h4 className="font-label-md text-label-md uppercase text-primary font-bold">Legal</h4>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/legal/privacy-policy">Privacy Policy</a>
          <a className="text-on-surface-variant font-body-md text-body-md hover:underline hover:text-primary transition-colors" href="/legal/terms-of-service">Terms of Service</a>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-container-margin py-stack-md border-t border-outline-variant flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-on-surface-variant font-body-md text-body-md opacity-70">
          &copy; 2024 Zao Agricultural Management. All rights reserved.
        </p>
        <div className="flex gap-4">
          <a className="text-on-surface-variant hover:text-primary transition-colors" href="#" aria-label="Visit our website">
            <HiOutlineGlobeAmericas className="w-5 h-5" aria-hidden="true" />
          </a>
          <a className="text-on-surface-variant hover:text-primary transition-colors" href="#" aria-label="Email us">
            <HiOutlineAtSymbol className="w-5 h-5" aria-hidden="true" />
          </a>
        </div>
      </div>
    </footer>
  )
}

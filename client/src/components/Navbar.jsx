import { useState } from 'react'
import { Link } from 'react-router-dom'
import { HiOutlineBars3, HiOutlineXMark } from 'react-icons/hi2'

const links = [
  { to: '/solutions', label: 'Solutions' },
  { to: '/farmers', label: 'For Farmers' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
]

export default function Navbar({ activeLink }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <nav aria-label="Main navigation" className="sticky top-0 z-50 bg-white/80 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-container-margin py-stack-md max-w-7xl mx-auto">
        <Link to="/" className="font-headline-sm text-headline-sm font-bold text-primary">
          Zao
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-stack-lg">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={
                activeLink === link.to
                  ? 'font-body-md text-body-md text-primary font-bold border-b-2 border-primary pb-1 transition-colors'
                  : 'font-body-md text-body-md text-on-surface-variant hover:text-primary transition-colors'
              }
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/farmer/login"
            className="px-4 py-2 rounded-lg border border-primary text-primary font-body-md text-body-md font-bold hover:bg-primary/5 transition-colors"
          >
            Farmer Login
          </Link>
          <Link
            to="/admin/login"
            className="px-4 py-2 rounded-lg bg-primary text-on-primary font-body-md text-body-md font-bold hover:bg-primary/90 transition-colors"
          >
            Staff Login
          </Link>
          <Link to="/contact" className="bg-primary text-on-primary font-body-md text-body-md px-stack-md py-stack-sm rounded-lg active:scale-95 duration-150 transition-all hover:shadow-lg">
            Request Demo
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden p-2 rounded-lg hover:bg-surface-container transition-colors text-on-surface-variant"
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <HiOutlineXMark className="w-6 h-6" aria-hidden="true" /> : <HiOutlineBars3 className="w-6 h-6" aria-hidden="true" />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-white/95 backdrop-blur-md border-t border-outline-variant/20 shadow-lg">
          <div className="px-container-margin py-4 space-y-1">
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={
                  activeLink === link.to
                    ? 'block px-4 py-3 rounded-lg font-body-md text-body-md text-primary font-bold bg-primary/5 transition-colors'
                    : 'block px-4 py-3 rounded-lg font-body-md text-body-md text-on-surface-variant hover:bg-surface-container hover:text-primary transition-colors'
                }
              >
                {link.label}
              </Link>
            ))}
            <hr className="my-3 border-outline-variant/20" />
            <Link
              to="/farmer/login"
              onClick={() => setMenuOpen(false)}
              className="block px-4 py-3 rounded-lg font-body-md text-body-md text-primary font-bold border border-primary text-center hover:bg-primary/5 transition-colors"
            >
              Farmer Login
            </Link>
            <Link
              to="/admin/login"
              onClick={() => setMenuOpen(false)}
              className="block px-4 py-3 rounded-lg font-body-md text-body-md text-on-primary font-bold bg-primary text-center hover:bg-primary/90 transition-colors"
            >
              Staff Login
            </Link>
            <Link to="/contact" onClick={() => setMenuOpen(false)} className="w-full mt-1 px-4 py-3 rounded-lg bg-primary text-on-primary font-body-md text-body-md font-bold active:scale-95 duration-150 transition-all hover:shadow-lg text-center">
              Request Demo
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

import { Link } from 'react-router-dom'

const links = [
  { to: '/solutions', label: 'Solutions' },
  { to: '/farmers', label: 'For Farmers' },
  { to: '/about', label: 'About' },
]

export default function Navbar({ activeLink }) {
  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-container-margin py-stack-md max-w-7xl mx-auto">
        <Link to="/" className="font-headline-sm text-headline-sm font-bold text-primary">
          Zao
        </Link>
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
        <button className="bg-primary text-on-primary font-body-md text-body-md px-stack-md py-stack-sm rounded-lg active:scale-95 duration-150 transition-all hover:shadow-lg">
          Request Demo
        </button>
      </div>
    </nav>
  )
}

export default function SlideOutPanel({ open, onClose, title, children, width = 'max-w-lg' }) {
  return (
    <>
      {open && <div className="fixed inset-0 bg-black/20 z-[55]" onClick={onClose} />}
      <div
        className={`fixed top-0 right-0 h-full bg-surface-container-lowest border-l border-outline-variant shadow-xl z-[55] transition-transform duration-300 ease-in-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        } ${width} w-full`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant">
          <h3 className="font-headline-sm text-headline-sm text-on-surface">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-surface-container-high rounded-lg transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>
        <div className="overflow-y-auto h-[calc(100%-65px)] p-6">
          {children}
        </div>
      </div>
    </>
  )
}

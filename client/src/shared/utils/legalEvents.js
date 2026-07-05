const LEGAL_INVALIDATE = 'legal:invalidate'

export function emitLegalInvalidate() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(LEGAL_INVALIDATE))
  }
}

export { LEGAL_INVALIDATE }

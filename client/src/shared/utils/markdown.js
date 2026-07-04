// Minimal markdown -> HTML for legal documents (no external dependency).
// Handles: # ## ### headings, blank-line paragraphs, **bold**, *italic*.
// Intentionally small; legal docs are simple prose. For richer markdown,
// swap this for a proper renderer (e.g. marked) later.

function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInline(text) {
  let s = escapeHtml(text)
  // Bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // Italic: *text*  (avoid matching inside ** already handled)
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
  return s
}

export function markdownToHtml(md) {
  if (!md) return ''
  const lines = md.split('\n')
  const out = []
  let para = []
  let inList = false
  let listItems = []

  const flushPara = () => {
    if (para.length) {
      out.push(`<p>${renderInline(para.join(' '))}</p>`)
      para = []
    }
  }
  const flushList = () => {
    if (listItems.length) {
      out.push('<ul>' + listItems.map((i) => `<li>${renderInline(i)}</li>`).join('') + '</ul>')
      listItems = []
    }
    inList = false
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    if (line === '') {
      flushPara()
      flushList()
      continue
    }
    let m
    if ((m = /^(###)\s+(.*)$/.exec(line))) {
      flushPara(); flushList()
      out.push(`<h3>${renderInline(m[2])}</h3>`)
    } else if ((m = /^(##)\s+(.*)$/.exec(line))) {
      flushPara(); flushList()
      out.push(`<h2>${renderInline(m[2])}</h2>`)
    } else if ((m = /^(#)\s+(.*)$/.exec(line))) {
      flushPara(); flushList()
      out.push(`<h1>${renderInline(m[2])}</h1>`)
    } else if (/^[-*]\s+/.test(line)) {
      flushPara()
      inList = true
      listItems.push(line.replace(/^[-*]\s+/, ''))
    } else {
      flushList()
      para.push(line.trim())
    }
  }
  flushPara()
  flushList()
  return out.join('\n')
}

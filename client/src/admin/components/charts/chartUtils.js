export function normalizeStackedData(data, keys, defaultValues = {}) {
  const defaults = {}
  for (const k of keys) {
    defaults[k] = defaultValues[k] ?? 0
  }
  return data.map((point) => {
    const normalized = { ...defaults, ...point }
    for (const k of keys) {
      if (normalized[k] == null) normalized[k] = defaults[k]
    }
    return normalized
  })
}

export function toPercent(value, total) {
  if (!total) return ''
  return `${((value / total) * 100).toFixed(1)}%`
}

export function abbreviateMonth(label) {
  if (!label) return ''
  const parts = label.split(' ')
  if (parts.length >= 2) {
    return `${parts[0].slice(0, 3)} ${parts[1]}`
  }
  return label.slice(0, 3)
}

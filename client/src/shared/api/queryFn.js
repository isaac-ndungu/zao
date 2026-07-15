export function createQueryFn(apiFetch) {
  return async ({ queryKey }) => {
    const [url, params] = queryKey
    const resolved = params ? `${url}?${new URLSearchParams(params)}` : url
    const res = await apiFetch(resolved)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      const err = new Error(body.detail || `Error ${res.status}`)
      err.status = res.status
      throw err
    }
    return res.json()
  }
}

export function createMutationFn(apiFetch, { method = 'POST' } = {}) {
  return async ({ url, body, formData }) => {
    const opts = { method }
    if (formData) {
      opts.headers = {}
      opts.body = formData
    } else if (body) {
      opts.body = JSON.stringify(body)
    }
    const res = await apiFetch(url, opts)
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      const err = new Error(data.detail || data.error || `Error ${res.status}`)
      err.status = res.status
      err.data = data
      throw err
    }
    return res.json()
  }
}

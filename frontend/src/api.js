export const API_HOST = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
const normalizedHost = API_HOST ? (API_HOST.startsWith('http') ? API_HOST : `https://${API_HOST}`) : ''
const BASE = `${normalizedHost}/api/demo`

export const getFullUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${normalizedHost}${path.startsWith('/') ? '' : '/'}${path}`
}

async function req(path, opts) {
  const r = await fetch(BASE + path, opts)
  if (!r.ok) {
    let msg = r.statusText
    try { msg = (await r.json()).detail || msg } catch { /* ignore */ }
    throw new Error(msg)
  }
  return r.json()
}
const post = (path, body) => req(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) })
const qs = (o) => {
  const p = new URLSearchParams()
  Object.entries(o || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, v) })
  const s = p.toString()
  return s ? '?' + s : ''
}

export const api = {
  mode: (requested) => req('/mode' + qs({ requested })),
  overview: () => req('/overview'),
  caseInfo: () => req('/case'),
  evidence: (params) => req('/evidence' + qs(params)),
  evidenceDetail: async (id) => {
    const d = await req(`/evidence/${id}`)
    if (d && d.file_url) d.file_url = getFullUrl(d.file_url)
    return d
  },
  verify: (id) => req(`/evidence/${id}/verify`),
  entities: (type) => req('/entities' + qs({ type })),
  entity: (id) => req(`/entities/${id}`),
  identity: () => req('/identity'),
  decide: (id, decision) => post(`/identity/${id}/decision`, { decision }),
  graph: () => req('/graph'),
  neighbors: (id) => req(`/graph/neighbors/${id}`),
  timeline: (params) => req('/timeline' + qs(params)),
  contradictions: () => req('/contradictions'),
  review: (id, status) => post(`/contradictions/${id}/review`, { status }),
  hypotheses: () => req('/hypotheses'),
  challenge: (id) => post(`/hypotheses/${id}/challenge`),
  gaps: () => req('/gaps'),
  ask: (question, mode) => post('/assistant', { question, mode }),
  reconstruct: (mode) => post('/reconstruction/run', { mode }),
  generateReport: async () => {
    const r = await post('/report/generate')
    if (r && r.download_url) r.download_url = getFullUrl(r.download_url)
    return r
  },
  reset: () => post('/reset'),
  audit: () => req('/audit'),
}

export const EV_RE = /\bEV-\d{4}\b/g
export const fmtTime = (iso) => (iso ? iso.slice(11, 19) : '')
export const fmtDateTime = (iso) => (iso ? iso.slice(0, 10) + ' ' + iso.slice(11, 19) : '')

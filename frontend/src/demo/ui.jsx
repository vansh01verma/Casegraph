import React, { createContext, useContext, useEffect, useState } from 'react'
import { api, EV_RE, fmtDateTime } from '../api'

const EvidenceCtx = createContext({ open: () => {} })
export const useEvidence = () => useContext(EvidenceCtx)

export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ loading: true, data: null, error: null })
  useEffect(() => {
    let live = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then((data) => live && setState({ loading: false, data, error: null }))
      .catch((error) => live && setState({ loading: false, data: null, error }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

export function Loading({ state }) {
  if (state.loading) return <div className="p-8 text-slate-400 animate-pulse">Loading demo data…</div>
  if (state.error) return <div className="p-8 text-red-300">Could not load demo data: {String(state.error.message || state.error)}. Is the backend running?</div>
  return null
}

export const Badge = ({ children, tone = 'slate', className = '' }) => {
  const tones = {
    slate: 'bg-slate-500/15 text-slate-300 border-slate-500/30', cyan: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30', red: 'bg-red-500/15 text-red-300 border-red-500/30',
    green: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', violet: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${tones[tone]} ${className}`}>{children}</span>
}

export const SyntheticTag = () => <Badge tone="amber">SYNTHETIC DEMO DATA</Badge>

export function EvChip({ id }) {
  const { open } = useEvidence()
  return (
    <button onClick={() => open(id)} className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/25 transition-colors" title="Open evidence">
      {id}
    </button>
  )
}
export const EvChips = ({ ids = [] }) => <span className="inline-flex flex-wrap gap-1">{ids.map((i) => <EvChip key={i} id={i} />)}</span>

/** Render text, turning EV-0000 mentions into clickable chips. */
export function LinkedText({ text }) {
  const parts = []
  let last = 0
  for (const m of text.matchAll(EV_RE)) {
    parts.push(text.slice(last, m.index))
    parts.push(<EvChip key={m.index} id={m[0]} />)
    last = m.index + m[0].length
  }
  parts.push(text.slice(last))
  return <span className="whitespace-pre-wrap">{parts}</span>
}

export const PageHeader = ({ title, subtitle, children }) => (
  <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
    <div>
      <h1 className="text-xl font-semibold text-white tracking-tight">{title}</h1>
      {subtitle && <p className="text-sm text-slate-400 mt-1 max-w-3xl">{subtitle}</p>}
    </div>
    <div className="flex items-center gap-2">{children}</div>
  </div>
)

export const ConfidenceBar = ({ value, tone = 'cyan' }) => (
  <div className="flex items-center gap-2" title={`Confidence ${value.toFixed(2)} (seeded / computed estimate, not a probability)`}>
    <div className="h-1.5 w-24 bg-navy-900 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${tone === 'amber' ? 'bg-amber-400' : 'bg-cyan-400'}`} style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
    <span className="text-xs font-mono text-slate-300">{value.toFixed(2)}</span>
  </div>
)

export function EvidenceProvider({ children }) {
  const [id, setId] = useState(null)
  const [d, setD] = useState(null)
  const [ver, setVer] = useState(null)
  const [err, setErr] = useState(null)
  useEffect(() => {
    if (!id) return
    setD(null); setVer(null); setErr(null)
    api.evidenceDetail(id).then(setD).catch(setErr)
  }, [id])
  return (
    <EvidenceCtx.Provider value={{ open: setId }}>
      {children}
      {id && (
        <div className="fixed inset-0 z-50 flex justify-end" onClick={() => setId(null)}>
          <div className="absolute inset-0 bg-black/50" />
          <aside onClick={(e) => e.stopPropagation()} className="relative w-full max-w-xl h-full overflow-y-auto bg-navy-900 border-l border-navy-600 p-5 fade-in" data-testid="evidence-drawer">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-mono text-cyan-300 text-lg">{id}</div>
                <SyntheticTag />
              </div>
              <button className="btn" onClick={() => setId(null)}>Close</button>
            </div>
            {err && <p className="mt-4 text-red-300">{String(err.message)}</p>}
            {!d && !err && <p className="mt-4 text-slate-400">Loading…</p>}
            {d && (
              <div className="mt-4 space-y-4 text-sm">
                <div>
                  <Badge tone="cyan">{d.category_label}</Badge> <Badge>{d.processing_status}</Badge>
                  <h3 className="mt-2 text-white font-medium">{d.title}</h3>
                  <p className="text-slate-300 mt-1">{d.summary}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="card p-3"><div className="text-xs text-slate-400">Original timestamp (source clock)</div><div className="font-mono">{fmtDateTime(d.original_ts)}</div></div>
                  <div className="card p-3"><div className="text-xs text-slate-400">Corrected timestamp (master clock)</div><div className="font-mono text-cyan-300">{fmtDateTime(d.corrected_ts)}</div>
                    {d.timestamp_corrected && <div className="text-xs text-amber-300 mt-1">Offset {d.clock_offset_seconds}s applied to {d.source}</div>}</div>
                </div>
                {d.file_url && <img src={d.file_url} alt="Synthetic CCTV frame" className="rounded-lg border border-navy-600 w-full" />}
                <div>
                  <div className="text-xs text-slate-400 mb-1">SHA-256</div>
                  <div className="font-mono text-[11px] break-all bg-navy-950 p-2 rounded border border-navy-600">{d.sha256}</div>
                  <button className="btn mt-2" onClick={() => api.verify(id).then(setVer)}>Recompute &amp; verify hash</button>
                  {ver && <span className={`ml-2 text-xs ${ver.match ? 'text-emerald-300' : 'text-red-300'}`}>{ver.match ? 'Hash matches stored value' : 'HASH MISMATCH'}</span>}
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">Record content</div>
                  <pre className="font-mono text-[11px] bg-navy-950 p-3 rounded border border-navy-600 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(d.content, null, 2)}</pre>
                </div>
                {(d.cited_in.contradictions.length > 0 || d.cited_in.hypotheses.length > 0) && (
                  <div className="text-xs text-slate-300">Cited in: {[...d.cited_in.contradictions, ...d.cited_in.hypotheses].map((x) => <Badge key={x} tone="violet" className="mr-1">{x}</Badge>)}</div>
                )}
                <div>
                  <div className="text-xs text-slate-400 mb-1">Chain of custody</div>
                  <ol className="border-l border-navy-600 ml-1 space-y-2">
                    {d.custody.map((c, i) => (
                      <li key={i} className="pl-3 relative"><span className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-cyan-400" />
                        <div className="text-xs"><span className="text-slate-100">{c.action.replace(/_/g, ' ')}</span> · <span className="font-mono text-slate-400">{fmtDateTime(c.ts)}</span></div>
                        <div className="text-[11px] text-slate-400">{c.actor} — {c.note}</div></li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}
    </EvidenceCtx.Provider>
  )
}

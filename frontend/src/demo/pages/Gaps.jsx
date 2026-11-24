import React from 'react'
import { Link } from 'react-router-dom'
import { api, fmtDateTime } from '../../api'
import { Badge, EvChips, Loading, PageHeader, SyntheticTag, useAsync } from '../ui.jsx'

const KIND = { cctv: 'Missing CCTV', financial: 'Missing financial records', phone: 'Unknown phone numbers', location: 'Incomplete location records', identity: 'Unverified identity connections' }
const SEV = { high: 'red', medium: 'amber', low: 'slate' }

export default function Gaps() {
  const st = useAsync(() => api.gaps(), [])
  if (st.loading || st.error) return <Loading state={st} />
  const g = st.data
  return (
    <div className="fade-in">
      <PageHeader title="Evidence Gap Analysis" subtitle={`${g.unresolved} of ${g.total} gaps are unresolved. CCTV gaps are computed from the time between consecutive frames; others from missing source records.`}><SyntheticTag /></PageHeader>
      <div className="space-y-6" data-tour="gaps-list">
        {Object.keys(KIND).map((k) => { const items = g.items.filter((x) => x.kind === k); if (!items.length) return null; return (
          <section key={k}><h2 className="text-sm font-medium text-white mb-2">{KIND[k]} <span className="text-slate-500">({items.length})</span></h2>
            <div className="grid lg:grid-cols-2 gap-3">{items.map((x) => (
              <div key={x.id} className="card p-4" data-testid="gap"><div className="flex flex-wrap items-center gap-2"><Badge tone={SEV[x.severity]}>{x.severity}</Badge><Badge tone={x.resolved ? 'green' : 'amber'}>{x.resolved ? 'resolved' : 'open'}</Badge><span className="font-mono text-[11px] text-slate-500">{x.id}</span></div>
                <h3 className="text-sm text-white mt-2">{x.title}</h3>
                {x.window_start && <div className="text-[11px] font-mono text-slate-400 mt-1">{fmtDateTime(x.window_start)}{x.window_end && x.window_end !== x.window_start ? ` → ${x.window_end.slice(11, 19)}` : ''}</div>}
                <p className="text-xs text-slate-300 mt-2">{x.detail}</p>
                {x.evidence_ids.length > 0 && <div className="mt-2 flex flex-wrap items-center gap-1 text-xs text-slate-400">Related: <EvChips ids={x.evidence_ids.slice(0, 6)} /></div>}
                <div className="mt-3 text-xs"><div className="text-cyan-300 font-medium mb-1">Recommended next steps</div><ul className="list-disc ml-4 space-y-0.5 text-slate-300">{x.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
                  {k === 'identity' && <Link to="/demo/identity" className="text-cyan-300 hover:underline mt-1 inline-block">Review in Identity Resolution →</Link>}</div></div>))}</div></section>) })}
      </div>
    </div>
  )
}

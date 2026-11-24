import React, { useState } from 'react'
import { api, fmtDateTime } from '../../api'
import { Badge, ConfidenceBar, EvChip, EvChips, Loading, PageHeader, SyntheticTag, useAsync, useEvidence } from '../ui.jsx'

const STATUS = { needs_review: ['amber', 'Needs review'], confirmed_conflict: ['red', 'Conflict confirmed by analyst'], dismissed: ['slate', 'Dismissed by analyst'], resolved_by_correction: ['green', 'Resolved by clock correction'] }

function Row({ id, label }) {
  const { open } = useEvidence()
  const st = useAsync(() => api.evidenceDetail(id), [id])
  const d = st.data
  return (
    <li className="flex gap-2 py-1.5 text-sm cursor-pointer hover:bg-navy-700/40 rounded px-1" onClick={() => open(id)}>
      <EvChip id={id} /><div className="min-w-0"><div className="truncate text-slate-200">{d ? d.summary : '…'}</div>
        {d && <div className="text-[11px] font-mono text-slate-500">{d.timestamp_corrected ? `device ${fmtDateTime(d.original_ts)} → corrected ${fmtDateTime(d.corrected_ts)}` : fmtDateTime(d.corrected_ts)}</div>}</div>
      {label && <Badge tone={label[0]} className="ml-auto shrink-0 self-start">{label[1]}</Badge>}</li>)
}

export default function Contradictions() {
  const [v, setV] = useState(0)
  const st = useAsync(() => api.contradictions(), [v])
  if (st.loading && !st.data) return <Loading state={st} />
  if (st.error) return <Loading state={st} />
  const review = async (id, status) => { await api.review(id, status); setV((x) => x + 1) }
  return (
    <div className="fade-in">
      <PageHeader title="Contradiction Checker" subtitle="Statements compared with records. A conflict is a lead for review: device location is not proof of where a person physically was."><SyntheticTag /></PageHeader>
      <div className="space-y-5" data-tour="contradiction-list">
        {st.data.items.map((c) => { const [tone, label] = STATUS[c.review_status] || ['slate', c.review_status]; return (
          <section key={c.id} className="card p-5" data-testid="contradiction">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><Badge tone="violet">{c.id}</Badge><h3 className="text-white font-medium mt-2 max-w-3xl">{c.title}</h3></div>
              <div className="text-right"><Badge tone={tone}>{label}</Badge><div className="mt-2"><ConfidenceBar value={c.confidence} /></div></div></div>
            <blockquote className="mt-3 border-l-2 border-amber-400/60 pl-3 text-sm text-slate-200 italic">{c.statement}</blockquote>
            <div className="grid md:grid-cols-2 gap-5 mt-4">
              <div><h4 className="text-xs uppercase tracking-wide text-red-300 mb-1">Statement / source record</h4><ul><Row id={c.statement_evidence_id} /></ul>
                <h4 className="text-xs uppercase tracking-wide text-red-300 mt-3 mb-1">Conflicting records</h4><ul>{c.conflicting_evidence_ids.map((i) => <Row key={i} id={i} />)}</ul></div>
              <div><h4 className="text-xs uppercase tracking-wide text-emerald-300 mb-1">Records pointing the other way</h4>
                <ul>{c.supporting_evidence_ids.length ? c.supporting_evidence_ids.map((i) => <Row key={i} id={i} />) : <li className="text-sm text-slate-500">None recorded.</li>}</ul>
                <h4 className="text-xs uppercase tracking-wide text-slate-400 mt-3 mb-1">Time information</h4>
                <dl className="text-xs font-mono space-y-0.5">{Object.entries(c.time_info).filter(([k]) => k !== 'note').map(([k, val]) => (<div key={k} className="flex justify-between gap-3"><dt className="text-slate-500">{k.replace(/_/g, ' ')}</dt><dd className="text-slate-200">{String(val).replace('T', ' ')}</dd></div>))}</dl>
                {c.time_info.note && <p className="text-xs text-amber-200/90 mt-2">{c.time_info.note}</p>}</div>
            </div>
            <p className="text-sm text-slate-300 mt-4"><b className="text-white">Explanation. </b>{c.explanation}</p>
            <div className="mt-3 rounded-lg bg-amber-500/10 border border-amber-500/30 p-3"><h4 className="text-xs font-medium text-amber-300 mb-1">Why this is not a conclusion</h4>
              <ul className="list-disc ml-5 text-xs text-amber-100/90 space-y-0.5">{c.caveats.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
            {c.review_status !== 'resolved_by_correction' && (
              <div className="flex flex-wrap gap-2 mt-4"><button className="btn" onClick={() => review(c.id, 'confirmed_conflict')} data-testid={`confirm-${c.id}`}>Mark conflict confirmed</button>
                <button className="btn" onClick={() => review(c.id, 'dismissed')}>Dismiss</button>
                {c.review_status !== 'needs_review' && <button className="btn" onClick={() => review(c.id, 'needs_review')}>Back to needs review</button>}</div>)}
          </section>) })}
      </div>
    </div>
  )
}

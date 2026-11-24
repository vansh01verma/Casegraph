import React, { useState } from 'react'
import { api } from '../../api'
import { Badge, ConfidenceBar, EvChips, Loading, PageHeader, SyntheticTag, useAsync, useEvidence } from '../ui.jsx'

export default function People() {
  const list = useAsync(() => api.entities('person'), [])
  const [sel, setSel] = useState('P-B')
  const prof = useAsync(() => api.entity(sel), [sel])
  const { open } = useEvidence()
  if (list.loading || list.error) return <Loading state={list} />
  const p = prof.data
  const group = (kind) => p?.relations.filter((r) => r.kind === kind) || []
  return (
    <div className="fade-in">
      <PageHeader title="People" subtitle="Select a person to see their phones, devices, accounts, relationships and linked evidence."><SyntheticTag /></PageHeader>
      <div className="grid lg:grid-cols-[260px_1fr] gap-4">
        <div className="space-y-2">{list.data.items.map((x) => (
          <button key={x.id} onClick={() => setSel(x.id)} className={`card w-full text-left p-3 transition-colors ${sel === x.id ? 'border-cyan-400' : 'hover:border-navy-600'}`}>
            <div className="text-sm text-white">{x.label}</div><div className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{x.role}</div></button>))}</div>
        <div data-tour="person-profile">
          {prof.loading && <div className="text-slate-400 p-4">Loading…</div>}
          {p && (
            <div className="space-y-4">
              <div className="card p-4"><h2 className="text-lg text-white font-semibold">{p.label}</h2><p className="text-sm text-slate-400">{p.role}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {[...group('owns_phone'), ...group('uses_device'), ...group('holds_account')].map((r) => <Badge key={r.id} tone="cyan">{r.kind.replace(/_/g, ' ')}: {r.other}</Badge>)}
                  {p.id === 'P-B' && <Badge tone="violet">alias “Raju”</Badge>}</div></div>
              {p.identity_matches.length > 0 && (
                <div className="card p-4"><h3 className="text-sm font-medium text-white mb-2">Possible identity connections</h3>
                  {p.identity_matches.map((m) => (<div key={m.id} className="flex flex-wrap items-center gap-3 py-1.5 text-sm"><Badge tone="violet">{m.id}</Badge>
                    <span>{m.entity_a_label} ↔ {m.entity_b_label}</span><ConfidenceBar value={m.score} /><Badge tone={m.status === 'accepted' ? 'green' : m.status === 'rejected' ? 'red' : 'amber'}>{m.status}</Badge></div>))}</div>)}
              <div className="card p-4"><h3 className="text-sm font-medium text-white mb-2">Relationships</h3>
                <ul className="space-y-1.5 text-sm">{p.relations.filter((r) => !['owns_phone', 'uses_device', 'holds_account'].includes(r.kind)).map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center gap-2"><Badge>{r.kind.replace(/_/g, ' ')}</Badge><span className="font-mono text-xs">{r.other}</span>
                    <ConfidenceBar value={r.confidence} /><EvChips ids={r.evidence_ids.slice(0, 3)} /></li>))}</ul></div>
              <div className="card p-4"><h3 className="text-sm font-medium text-white mb-2">Linked evidence ({p.evidence_count})</h3>
                <ul className="divide-y divide-navy-700">{p.evidence.slice(0, 12).map((e) => (
                  <li key={e.id} className="py-1.5 text-sm flex gap-2 cursor-pointer hover:bg-navy-700/40" onClick={() => open(e.id)}>
                    <span className="font-mono text-cyan-300 w-20 shrink-0">{e.id}</span><span className="truncate">{e.summary}</span></li>))}</ul></div>
            </div>)}
        </div>
      </div>
    </div>
  )
}

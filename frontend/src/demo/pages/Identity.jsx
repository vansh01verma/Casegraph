import React, { useState } from 'react'
import { api } from '../../api'
import { Badge, ConfidenceBar, EvChips, Loading, PageHeader, SyntheticTag, useAsync } from '../ui.jsx'

const FEATURE_LABEL = {
  alias_usage_messages: 'Messages using alias', name_similarity: 'Name similarity', upi_display_name_contains_alias: 'UPI display name contains alias',
  contact_overlap_jaccard: 'Contact overlap (Jaccard)', self_identification_messages: 'Self-identification messages', tower_colocation_ratio: 'Same-tower ratio',
  second_number_first_seen_after_primary_active: 'Second number appears while primary is active', upi_display_name: 'UPI display name', registered_to_phone: 'Registered against',
  name_similarity_to_person: 'Name similarity to person', inbound_from_known_associates: 'Inbound from known associates', calls_made_to_person_f: 'Calls to Person F', same_tower_region_as_person_f: 'Same tower region as Person F',
}

export default function Identity() {
  const [v, setV] = useState(0)
  const st = useAsync(() => api.identity(), [v])
  const [busy, setBusy] = useState(null)
  if (st.loading && !st.data) return <Loading state={st} />
  if (st.error) return <Loading state={st} />
  const decide = async (id, d) => { setBusy(id); try { await api.decide(id, d); setV((x) => x + 1) } finally { setBusy(null) } }
  return (
    <div className="fade-in">
      <PageHeader title="Identity Resolution" subtitle="Possible links between aliases, numbers, accounts and people. Scores are computed from observable features; they are leads for an analyst to verify, not conclusions."><SyntheticTag /></PageHeader>
      <div className="grid xl:grid-cols-2 gap-4" data-tour="identity-cards">
        {st.data.items.map((m) => (
          <div key={m.id} className={`card p-4 ${m.status === 'accepted' ? 'border-emerald-500/50' : m.status === 'rejected' ? 'border-red-500/40 opacity-80' : ''}`} data-testid="identity-card">
            <div className="flex items-start justify-between gap-2"><div><Badge tone="violet">{m.id}</Badge>
              <h3 className="text-white font-medium mt-2">{m.entity_a_label} <span className="text-slate-500">↔</span> {m.entity_b_label}</h3></div>
              <Badge tone={m.status === 'accepted' ? 'green' : m.status === 'rejected' ? 'red' : 'amber'}>{m.status}</Badge></div>
            <div className="mt-3"><ConfidenceBar value={m.score} /></div>
            <p className="text-sm text-slate-300 mt-3">{m.explanation}</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-xs">{Object.entries(m.features).map(([k, val]) => (
              <React.Fragment key={k}><dt className="text-slate-400">{FEATURE_LABEL[k] || k}</dt><dd className="font-mono text-slate-200 text-right">{String(val)}</dd></React.Fragment>))}</dl>
            <div className="mt-3 text-xs text-slate-400 flex flex-wrap items-center gap-2">Evidence: {m.evidence_ids.length ? <EvChips ids={m.evidence_ids} /> : 'none cited'}</div>
            <div className="flex gap-2 mt-4">
              <button className="btn btn-primary" disabled={busy === m.id || m.status === 'accepted'} onClick={() => decide(m.id, 'accept')} data-testid={`accept-${m.id}`}>Accept match</button>
              <button className="btn btn-danger" disabled={busy === m.id || m.status === 'rejected'} onClick={() => decide(m.id, 'reject')} data-testid={`reject-${m.id}`}>Reject</button>
              {m.status !== 'proposed' && <button className="btn" onClick={() => decide(m.id, 'reset')}>Undo</button>}</div>
          </div>))}
      </div>
      <p className="text-xs text-slate-500 mt-4">Decisions apply inside the demo only: rejecting a match removes its edge from the graph and changes how the assistant attributes the UPI account. Use “Reset demo” to restore the original state.</p>
    </div>
  )
}

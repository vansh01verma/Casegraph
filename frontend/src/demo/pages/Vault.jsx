import React, { useEffect, useState } from 'react'
import { api, fmtDateTime } from '../../api'
import { Badge, Loading, PageHeader, SyntheticTag, useAsync, useEvidence } from '../ui.jsx'

const PAGE = 25
export default function Vault() {
  const { open } = useEvidence()
  const [q, setQ] = useState(''), [debounced, setDebounced] = useState('')
  const [cat, setCat] = useState(''), [person, setPerson] = useState(''), [page, setPage] = useState(0)
  useEffect(() => { const t = setTimeout(() => { setDebounced(q); setPage(0) }, 250); return () => clearTimeout(t) }, [q])
  const people = useAsync(() => api.entities('person'), [])
  const st = useAsync(() => api.evidence({ q: debounced, category: cat, person, limit: PAGE, offset: page * PAGE }), [debounced, cat, person, page])
  const d = st.data
  return (
    <div className="fade-in">
      <PageHeader title="Evidence Vault" subtitle="All synthetic records with original and corrected timestamps, SHA-256 hashes and processing status."><SyntheticTag /></PageHeader>
      <div className="flex flex-wrap gap-2 mb-3">
        <input className="input w-72" placeholder="Search text, ID, hash…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="vault-search" />
        <select className="input" value={cat} onChange={(e) => { setCat(e.target.value); setPage(0) }} data-testid="vault-category">
          <option value="">All categories</option>
          {d?.categories.map((c) => <option key={c.key} value={c.key}>{c.label} ({c.count})</option>)}
        </select>
        <select className="input" value={person} onChange={(e) => { setPerson(e.target.value); setPage(0) }}>
          <option value="">All people</option>
          {people.data?.items.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
        {d && <span className="self-center text-sm text-slate-400" data-testid="vault-total">{d.total} records</span>}
      </div>
      {st.error ? <Loading state={st} /> : (
        <div className="card overflow-x-auto" data-tour="vault-table">
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-400 text-left"><tr className="border-b border-navy-600">
              {['ID', 'Type', 'Summary', 'Original time', 'Corrected time', 'SHA-256', 'Status'].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>{d?.items.map((e) => (
              <tr key={e.id} className="border-b border-navy-700/60 hover:bg-navy-700/40 cursor-pointer" onClick={() => open(e.id)} data-testid="vault-row">
                <td className="px-3 py-2 font-mono text-cyan-300">{e.id}</td>
                <td className="px-3 py-2"><Badge tone="cyan">{e.category}</Badge></td>
                <td className="px-3 py-2 max-w-[460px] truncate" title={e.summary}>{e.summary}</td>
                <td className="px-3 py-2 font-mono text-xs text-slate-400 whitespace-nowrap">{fmtDateTime(e.original_ts)}</td>
                <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{fmtDateTime(e.corrected_ts)}{e.timestamp_corrected && <Badge tone="amber" className="ml-1">{e.clock_offset_seconds}s</Badge>}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-slate-500">{e.sha256.slice(0, 12)}…</td>
                <td className="px-3 py-2"><Badge tone="green">{e.processing_status}</Badge></td></tr>))}
              {d && d.items.length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-slate-400">No records match your search.</td></tr>}
            </tbody></table>
        </div>)}
      {d && <div className="flex items-center justify-between mt-3 text-sm text-slate-400">
        <span>Page {page + 1} of {Math.max(1, Math.ceil(d.total / PAGE))}</span>
        <div className="flex gap-2"><button className="btn" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
          <button className="btn" disabled={(page + 1) * PAGE >= d.total} onClick={() => setPage(page + 1)}>Next</button></div></div>}
    </div>
  )
}

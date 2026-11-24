import React, { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../../api'
import { Badge, EvChip, Loading, PageHeader, SyntheticTag, useAsync } from '../ui.jsx'

const TYPES = [['cdr', 'Calls', 'cyan'], ['whatsapp', 'Messages', 'green'], ['transaction', 'Transactions', 'amber'], ['gps', 'GPS', 'violet'],
  ['cctv', 'CCTV', 'slate'], ['statement', 'Statements', 'red'], ['device_log', 'Device logs', 'slate'], ['analysis', 'Findings', 'cyan']]
const TONE = Object.fromEntries(TYPES.map(([k, , t]) => [k, t]))
const toMin = (iso) => parseInt(iso.slice(11, 13)) * 60 + parseInt(iso.slice(14, 16))
const hhmm = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

export default function Timeline() {
  const [types, setTypes] = useState(new Set(TYPES.map((t) => t[0])))
  const [person, setPerson] = useState('')
  const people = useAsync(() => api.entities('person'), [])
  const st = useAsync(() => api.timeline({ persons: person }), [person])
  const [cursor, setCursor] = useState(1200)
  const [playing, setPlaying] = useState(false)
  const listRef = useRef(null)
  const events = useMemo(() => (st.data ? st.data.events.filter((e) => types.has(e.category)) : []), [st.data, types])
  const lo = 1200, hi = 1380

  useEffect(() => {
    if (!playing) return
    const t = setInterval(() => setCursor((c) => { if (c >= hi) { setPlaying(false); return hi } return c + 1 }), 120)
    return () => clearInterval(t)
  }, [playing])
  useEffect(() => { // keep newest visible event in view while playing
    if (playing && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [cursor, playing])

  if (st.error) return <Loading state={st} />
  const shown = events.filter((e) => toMin(e.ts) <= cursor)
  const toggle = (k) => setTypes((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n })
  return (
    <div className="fade-in">
      <PageHeader title="Timeline" subtitle="14 March 2026, 20:00–23:00 (master clock). Where a device clock was wrong, the corrected time is used and the original is shown beside it."><SyntheticTag /></PageHeader>
      <div className="card p-4 mb-4" data-tour="timeline-controls">
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn btn-primary w-24 justify-center" onClick={() => { if (cursor >= hi) setCursor(lo); setPlaying(!playing) }} data-testid="play">{playing ? 'Pause' : 'Play'}</button>
          <button className="btn" onClick={() => { setPlaying(false); setCursor(lo) }}>Restart</button>
          <input type="range" min={lo} max={hi} value={cursor} onChange={(e) => { setPlaying(false); setCursor(+e.target.value) }} className="flex-1 min-w-[200px] accent-cyan-400" data-testid="slider" />
          <span className="font-mono text-cyan-300 text-lg w-16" data-testid="cursor">{hhmm(cursor)}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          {TYPES.map(([k, label]) => (<button key={k} onClick={() => toggle(k)} data-testid={`tl-filter-${k}`}
            className={`px-2.5 py-1 rounded-full text-xs border ${types.has(k) ? 'border-cyan-400/60 text-cyan-200 bg-cyan-500/10' : 'border-navy-600 text-slate-500'}`}>{label}</button>))}
          <select className="input ml-auto" value={person} onChange={(e) => setPerson(e.target.value)} data-testid="tl-person">
            <option value="">All people</option>{people.data?.items.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select>
        </div>
        <div className="relative h-6 mt-3"> {/* mini-map of event density */}
          <div className="absolute inset-x-0 top-2.5 h-1 bg-navy-900 rounded" />
          {events.map((e) => <i key={e.id} className="absolute top-1.5 h-3 w-0.5 bg-cyan-400/50" style={{ left: `${((toMin(e.ts) - lo) / (hi - lo)) * 100}%` }} />)}
          <i className="absolute top-0 h-6 w-0.5 bg-amber-300" style={{ left: `${((cursor - lo) / (hi - lo)) * 100}%` }} />
        </div>
      </div>
      <div className="text-xs text-slate-400 mb-2" data-testid="tl-count">Showing {shown.length} of {events.length} events up to {hhmm(cursor)}</div>
      <ol ref={listRef} className="card divide-y divide-navy-700 max-h-[560px] overflow-y-auto" data-testid="tl-list">
        {shown.map((e) => (
          <li key={e.id} className={`px-4 py-2.5 text-sm flex gap-3 ${e.kind === 'finding' ? 'bg-cyan-500/5' : ''}`}>
            <div className="w-28 shrink-0"><div className="font-mono text-slate-100">{e.ts.slice(11, 19)}</div>
              {e.timestamp_corrected && <div className="text-[10px] text-amber-300 font-mono" title="Original time on the source device">device {e.original_ts.slice(11, 19)} ({e.clock_offset_seconds}s)</div>}</div>
            <div className="flex-1 min-w-0"><div className="flex flex-wrap items-center gap-2"><Badge tone={TONE[e.category] || 'slate'}>{e.category_label}</Badge>
              {e.kind === 'claim' && <Badge tone="red">claim, not a record</Badge>}{e.id.startsWith('EV-') ? <EvChip id={e.id} /> : <span className="font-mono text-[11px] text-slate-500">{e.id}</span>}</div>
              <p className="mt-1 text-slate-200">{e.summary}</p></div>
          </li>))}
        {shown.length === 0 && <li className="px-4 py-8 text-center text-slate-400">No events yet at this time — move the slider or press Play.</li>}
      </ol>
    </div>
  )
}

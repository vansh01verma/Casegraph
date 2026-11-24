import React, { useEffect, useRef, useState } from 'react'
import { api } from '../../api'
import { Badge, EvChips, LinkedText, PageHeader, SyntheticTag } from '../ui.jsx'
import { useMode } from '../DemoLayout.jsx'

const SUGGEST = ['What happened between 9 PM and 10 PM?', 'Who transferred money to Person B?', 'What contradictions were detected?', 'Which evidence supports Scenario 1?',
  'What is the relationship between Person A and Person C?', 'Which evidence is missing?', 'Summarize the investigation.']

export default function Assistant() {
  const { mode } = useMode()
  const [msgs, setMsgs] = useState([])
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])
  const ask = async (text) => {
    text = (text ?? q).trim(); if (!text || busy) return
    setQ(''); setMsgs((m) => [...m, { role: 'user', text }]); setBusy(true)
    try { const r = await api.ask(text, mode); setMsgs((m) => [...m, { role: 'bot', r }]) }
    catch (e) { setMsgs((m) => [...m, { role: 'bot', error: e.message }]) } finally { setBusy(false) }
  }
  return (
    <div className="fade-in">
      <PageHeader title="AI Investigator Assistant" subtitle="Answers come from the demo dataset only and cite evidence IDs. If the dataset has no answer, it says so."><SyntheticTag /></PageHeader>
      <div className="card flex flex-col h-[calc(100vh-290px)] min-h-[460px]">
        <div className="flex-1 overflow-y-auto p-4 space-y-4" data-testid="chat">
          {msgs.length === 0 && (<div><p className="text-sm text-slate-400 mb-3">Try a question:</p><div className="flex flex-wrap gap-2">{SUGGEST.map((s) => <button key={s} className="btn" onClick={() => ask(s)}>{s}</button>)}</div></div>)}
          {msgs.map((m, i) => m.role === 'user' ? (
            <div key={i} className="flex justify-end"><div className="max-w-[80%] rounded-xl bg-cyan-500/20 border border-cyan-400/40 px-3 py-2 text-sm">{m.text}</div></div>
          ) : (
            <div key={i} className="max-w-[92%]" data-testid="bot-msg">
              {m.error ? <div className="text-red-300 text-sm">{m.error}</div> : (<div className="rounded-xl bg-navy-900 border border-navy-600 px-4 py-3 text-sm text-slate-200">
                <LinkedText text={m.r.answer} />
                {m.r.warnings.map((w, j) => <div key={j} className="mt-2 text-xs text-amber-300">⚠ {w}</div>)}
                <div className="mt-3 pt-2 border-t border-navy-700 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                  <Badge tone={m.r.mode_used === 'precomputed' ? 'amber' : 'cyan'}>{m.r.mode_used}</Badge><span>{m.r.produced_by}</span>
                  {m.r.evidence_ids.length > 0 && <><span>· Sources:</span><EvChips ids={m.r.evidence_ids.slice(0, 12)} />{m.r.evidence_ids.length > 12 && <span>+{m.r.evidence_ids.length - 12} more</span>}</>}</div></div>)}
            </div>))}
          {busy && <div className="text-sm text-slate-400 animate-pulse">Searching the case records…</div>}
          <div ref={end} />
        </div>
        <form className="p-3 border-t border-navy-600 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask() }} data-tour="assistant-input">
          <input className="input flex-1" placeholder="Ask about the demo case…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="chat-input" />
          <button className="btn btn-primary" disabled={busy || !q.trim()} data-testid="chat-send">Send</button></form>
      </div>
    </div>
  )
}

import React, { useState } from 'react'
import { api } from '../../api'
import { Badge, ConfidenceBar, EvChips, PageHeader, SyntheticTag } from '../ui.jsx'
import { useMode } from '../DemoLayout.jsx'

const AGENTS = [['Extractor', 'Extract facts'], ['Correlator', 'Connect entities & events'], ['Hypothesis', 'Three possible scenarios'], ['Critic', 'Challenge each scenario'], ['Report', 'Final summary']]
const VERDICT = (v) => (/unsupported/.test(v) ? 'red' : /weakened/.test(v) ? 'amber' : 'green')

function Scenario({ h, challenge }) {
  const [crit, setCrit] = useState(null)
  const [busy, setBusy] = useState(false)
  const run = async () => { setBusy(true); try { setCrit(await api.challenge(h.id)) } finally { setBusy(false) } }
  const critic = crit?.critic || h.critic
  return (
    <div className="card p-4" data-testid="scenario">
      <div className="flex items-start justify-between gap-3"><h4 className="text-white font-medium">{h.title}</h4><ConfidenceBar value={h.confidence} tone="amber" /></div>
      <p className="text-sm text-slate-300 mt-2">{h.description}</p>
      <div className="grid md:grid-cols-2 gap-4 mt-3 text-xs">
        <div><div className="text-emerald-300 font-medium mb-1">Supporting evidence</div>{h.supporting.map((x) => <div key={x.evidence_id} className="flex gap-2 py-0.5"><EvChips ids={[x.evidence_id]} /><span className="text-slate-300">{x.note}</span></div>)}</div>
        <div><div className="text-red-300 font-medium mb-1">Contradicting evidence</div>{h.contradicting.map((x) => <div key={x.evidence_id} className="flex gap-2 py-0.5"><EvChips ids={[x.evidence_id]} /><span className="text-slate-300">{x.note}</span></div>)}</div>
      </div>
      <p className="text-xs text-slate-300 mt-3"><b className="text-white">Reasoning. </b>{h.reasoning}</p>
      <div className="mt-2 text-xs"><b className="text-white">Missing information: </b><span className="text-slate-300">{h.missing.join('; ')}</span></div>
      <div className="mt-3 pt-3 border-t border-navy-600">
        <button className="btn" onClick={run} disabled={busy} data-testid={`challenge-${h.id}`}>{busy ? 'Challenging…' : 'Challenge this scenario'}</button>
        {(crit || challenge) && critic.length > 0 && (
          <ul className="mt-3 space-y-2">{critic.map((c, i) => (
            <li key={i} className="rounded-lg bg-navy-900 border border-navy-600 p-3 text-xs"><div className="flex items-center justify-between gap-2"><span className="text-slate-100">Claim: {c.claim}</span><Badge tone={VERDICT(c.verdict)}>{c.verdict}</Badge></div>
              <p className="text-slate-300 mt-1">{c.challenge}</p><div className="mt-1.5"><EvChips ids={c.evidence_ids} /></div></li>))}</ul>)}
        {crit && <p className="text-[11px] text-slate-500 mt-2">Produced by: {crit.produced_by}</p>}
        {crit?.automatic_checks?.[0]?.flag && <p className="text-[11px] text-amber-300 mt-1">Rule check: {crit.automatic_checks[0].flag}</p>}
      </div>
    </div>)
}

export default function Reconstruction() {
  const { mode } = useMode()
  const [res, setRes] = useState(null)
  const [phase, setPhase] = useState(-1)
  const [err, setErr] = useState(null)
  const running = phase >= 0 && phase < AGENTS.length
  const run = async () => {
    setErr(null); setRes(null); setPhase(0)
    try {
      const p = api.reconstruct(mode)
      for (let i = 0; i < AGENTS.length; i++) { setPhase(i); await new Promise((r) => setTimeout(r, 650)) }
      setRes(await p); setPhase(AGENTS.length)
    } catch (e) { setErr(e.message); setPhase(-1) }
  }
  const step = (name) => res?.steps.find((s) => s.agent === name)
  return (
    <div className="fade-in">
      <PageHeader title="AI Reconstruction" subtitle="Five-agent workflow: Extractor → Correlator → Hypothesis → Critic → Report. Each step states how it was produced."><SyntheticTag /></PageHeader>
      <div className="card p-4" data-tour="reconstruction-run">
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn btn-primary" onClick={run} disabled={running} data-testid="run-reconstruction">{running ? 'Running…' : res ? 'Run again' : 'Run reconstruction'}</button>
          <span className="text-xs text-slate-400">Requested mode: <b className="text-cyan-300">{mode}</b></span></div>
        <ol className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-4">{AGENTS.map(([n, d], i) => (
          <li key={n} className={`rounded-lg border p-3 text-xs transition-colors ${phase > i ? 'border-emerald-500/50 bg-emerald-500/10' : phase === i ? 'border-cyan-400 bg-cyan-500/10 animate-pulse' : 'border-navy-600'}`}>
            <div className="text-[10px] text-slate-500">Agent {i + 1}</div><div className="text-white font-medium">{n}</div><div className="text-slate-400">{d}</div></li>))}</ol>
      </div>
      {err && <p className="mt-4 text-red-300">{err}</p>}
      {res && (
        <div className="mt-4 space-y-4">
          <div className={`rounded-xl border p-3 text-sm ${res.mode_used === 'precomputed' ? 'border-amber-500/40 bg-amber-500/10 text-amber-100' : 'border-cyan-500/40 bg-cyan-500/10 text-cyan-100'}`} data-testid="mode-banner">
            <b>{res.mode_label}.</b> {res.banner}{res.fallback_reason && <div className="text-xs mt-1">Fell back because: {res.fallback_reason}</div>}</div>
          {['Extractor', 'Correlator'].map((n) => { const s = step(n); const items = s.facts || s.links; return (
            <details key={n} className="card p-4" open={n === 'Extractor'}><summary className="cursor-pointer text-white font-medium">{n} Agent <span className="text-xs text-slate-400 font-normal">— {s.summary}</span></summary>
              <div className="text-[11px] text-slate-500 mt-1">Produced by: {s.produced_by}</div>
              <ul className="mt-2 divide-y divide-navy-700">{items.map((f, i) => <li key={i} className="py-1.5 text-sm flex flex-wrap gap-2 items-center"><span className="text-slate-200">{f.fact || f.link}</span><EvChips ids={f.evidence_ids.slice(0, 6)} /></li>)}</ul></details>) })}
          <div><h3 className="text-white font-medium mb-1">Hypothesis Agent — three scenarios</h3><div className="text-[11px] text-slate-500 mb-2">Produced by: {step('Hypothesis').produced_by}. Confidence values are estimates, not probabilities.</div>
            <div className="grid xl:grid-cols-3 gap-4">{step('Hypothesis').scenarios.map((h) => <Scenario key={h.id} h={h} challenge />)}</div></div>
          <div className="card p-4"><h3 className="text-white font-medium">Report Agent — summary</h3><div className="text-[11px] text-slate-500">Produced by: {step('Report').produced_by}</div>
            <p className="text-sm text-slate-200 mt-2">{step('Report').report.text}</p><div className="mt-2 flex flex-wrap gap-1 items-center text-xs text-slate-400">Sources: <EvChips ids={step('Report').report.evidence_ids} /></div></div>
        </div>)}
    </div>
  )
}

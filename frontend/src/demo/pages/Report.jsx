import React, { useState } from 'react'
import { api } from '../../api'
import { Badge, PageHeader, SyntheticTag } from '../ui.jsx'

const SECTIONS = ['Case details', 'Investigation summary', 'Corrected timeline', 'Identity relationships', 'Contradictions', 'Competing scenarios with supporting & contradicting evidence',
  'Confidence scores', 'Evidence gaps & recommended next steps', 'Evidence inventory with SHA-256 hashes', 'Chain-of-custody history']

export default function Report() {
  const [r, setR] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const gen = async () => { setBusy(true); setErr(null); try { setR(await api.generateReport()) } catch (e) { setErr(e.message) } finally { setBusy(false) } }
  return (
    <div className="fade-in">
      <PageHeader title="PDF Report" subtitle="Generate a professional investigation report from the current demo state (including your identity decisions and reviews)."><SyntheticTag /></PageHeader>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-5"><h3 className="text-white font-medium mb-2">Report contents</h3>
          <ul className="space-y-1 text-sm text-slate-300">{SECTIONS.map((s) => <li key={s} className="flex gap-2"><span className="text-cyan-400">✓</span>{s}</li>)}</ul>
          <p className="mt-3 text-xs text-amber-300">Every page is watermarked: SYNTHETIC DEMONSTRATION DATA – NOT A REAL INVESTIGATION.</p></div>
        <div className="card p-5" data-tour="report-generate">
          <button className="btn btn-primary" onClick={gen} disabled={busy} data-testid="generate-report">{busy ? 'Generating…' : r ? 'Regenerate report' : 'Generate PDF report'}</button>
          {err && <p className="text-red-300 text-sm mt-3">{err}</p>}
          {r && (<div className="mt-4 text-sm space-y-2" data-testid="report-ready"><div className="flex gap-2"><Badge tone="green">ready</Badge><span className="font-mono text-xs text-slate-400">{r.report_id}</span></div>
            <div className="text-slate-300">{r.pages} pages · {(r.bytes / 1024).toFixed(0)} KB</div>
            <div className="text-[11px] text-slate-500 break-all">SHA-256 {r.sha256}</div>
            <a className="btn btn-primary inline-flex" href={r.download_url} download data-testid="download-report">Download PDF</a></div>)}
        </div>
      </div>
    </div>
  )
}

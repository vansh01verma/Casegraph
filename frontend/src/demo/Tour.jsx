import React, { useEffect, useLayoutEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export const STEPS = [
  { route: '/demo', target: 'dashboard-metrics', title: '1. Dashboard', text: 'Every number here is computed from the demo database: evidence, people, devices, transactions, contradictions and open gaps.' },
  { route: '/demo/vault', target: 'vault-table', title: '2. Evidence Vault', text: 'Search and filter all records. Open any row to see its original and clock-corrected time, SHA-256 hash and chain of custody.' },
  { route: '/demo/people', target: 'person-profile', title: '3. Person profile', text: 'Pick a person to see their phones, devices, accounts, relationships and the evidence that mentions them.' },
  { route: '/demo/identity', target: 'identity-cards', title: '4. Identity Resolution', text: 'Possible same-identity links with a computed score and explanation. Accept or reject them — the graph, gaps and assistant respond.' },
  { route: '/demo/graph', target: 'graph-canvas', title: '5. Knowledge Graph', text: 'Click nodes, expand connections, filter types and open the evidence behind each relationship and its confidence.' },
  { route: '/demo/timeline', target: 'timeline-controls', title: '6. Timeline', text: 'Replay the evening with the slider or play button. Corrected timestamps are shown next to the original device times.' },
  { route: '/demo/contradictions', target: 'contradiction-list', title: '7. Contradiction Checker', text: 'Statements are compared with records. Note the caveats: device location is not proof of a person’s presence.' },
  { route: '/demo/reconstruction', target: 'reconstruction-run', title: '8. AI Reconstruction', text: 'Run the five-agent workflow. Each step says how it was produced, and you can challenge any scenario with the critic.' },
  { route: '/demo/gaps', target: 'gaps-list', title: '9. Evidence Gap Analysis', text: 'What is missing, from the lobby CCTV gap to unknown numbers, with recommended next steps.' },
  { route: '/demo/assistant', target: 'assistant-input', title: '10. AI Investigator Assistant', text: 'Ask about the case. Answers cite real evidence IDs and say so when the dataset has no answer.' },
  { route: '/demo/report', target: 'report-generate', title: '11. PDF Report', text: 'Generate a watermarked investigation report with hashes, custody history, timeline, scenarios and gaps.' },
]

export default function Tour({ onClose }) {
  const [i, setI] = useState(0)
  const [rect, setRect] = useState(null)
  const nav = useNavigate()
  const step = STEPS[i]

  useEffect(() => { nav(step.route) }, [i]) // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    let tries = 0, timer
    const find = () => {
      const el = document.querySelector(`[data-tour="${step.target}"]`)
      if (el) {
        el.scrollIntoView({ block: 'center', behavior: 'smooth' })
        const upd = () => { const r = el.getBoundingClientRect(); setRect({ top: r.top, left: r.left, width: r.width, height: r.height }) }
        upd(); timer = setInterval(upd, 250)
      } else if (tries++ < 20) { timer = setTimeout(find, 150) } else { setRect(null) }
    }
    setRect(null); find()
    return () => { clearInterval(timer); clearTimeout(timer) }
  }, [i]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onClose(); if (e.key === 'ArrowRight') setI((x) => Math.min(x + 1, STEPS.length - 1)); if (e.key === 'ArrowLeft') setI((x) => Math.max(x - 1, 0)) }
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k)
  }, [onClose])

  const pad = 6
  const boxStyle = rect ? { top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2 } : null
  const popBelow = rect ? rect.top + rect.height + 200 < window.innerHeight : true
  const popStyle = rect
    ? { top: popBelow ? Math.min(rect.top + rect.height + 16, window.innerHeight - 220) : Math.max(rect.top - 200, 70), left: Math.min(Math.max(rect.left, 16), window.innerWidth - 400) }
    : { top: 120, left: Math.max(window.innerWidth / 2 - 190, 16) }

  return (
    <div className="fixed inset-0 z-[60] pointer-events-none" data-testid="tour">
      {boxStyle && <div className="absolute rounded-xl border-2 border-cyan-300 transition-all duration-300" style={{ ...boxStyle, boxShadow: '0 0 0 9999px rgba(3,8,18,0.72)' }} />}
      {!boxStyle && <div className="absolute inset-0 bg-black/60" />}
      <div className="absolute w-[380px] card bg-navy-900 p-4 pointer-events-auto fade-in" style={popStyle}>
        <div className="text-[11px] text-cyan-300 font-mono">Step {i + 1} of {STEPS.length}</div>
        <h3 className="text-white font-semibold mt-1">{step.title}</h3>
        <p className="text-sm text-slate-300 mt-1">{step.text}</p>
        <div className="flex items-center justify-between mt-4">
          <button className="text-xs text-slate-400 hover:text-white" onClick={onClose} data-testid="tour-skip">Skip tour</button>
          <div className="flex gap-2">
            <button className="btn" disabled={i === 0} onClick={() => setI(i - 1)}>Back</button>
            {i < STEPS.length - 1
              ? <button className="btn btn-primary" onClick={() => setI(i + 1)} data-testid="tour-next">Next</button>
              : <button className="btn btn-primary" onClick={onClose} data-testid="tour-done">Finish</button>}
          </div>
        </div>
      </div>
    </div>
  )
}

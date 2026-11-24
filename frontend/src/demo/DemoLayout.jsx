import React, { createContext, useContext, useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Badge, EvidenceProvider } from './ui.jsx'
import Tour from './Tour.jsx'

const ModeCtx = createContext({ mode: 'precomputed', setMode: () => {}, info: null })
export const useMode = () => useContext(ModeCtx)
export const ResetCtx = createContext(0)

const NAV = [
  ['', 'Dashboard'], ['vault', 'Evidence Vault'], ['people', 'People'], ['identity', 'Identity'], ['graph', 'Graph'],
  ['timeline', 'Timeline'], ['contradictions', 'Contradictions'], ['reconstruction', 'Reconstruction'],
  ['gaps', 'Gaps'], ['assistant', 'Assistant'], ['report', 'PDF Report'],
]

export default function DemoLayout() {
  const [info, setInfo] = useState(null)
  const [mode, setMode] = useState('precomputed')
  const [tour, setTour] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const [toast, setToast] = useState(null)
  const nav = useNavigate()

  useEffect(() => { api.mode().then(setInfo).catch(() => {}) }, [])

  const doReset = async () => {
    if (!window.confirm('Reset the demo to its original state? Your accept/reject decisions and reviews will be cleared. Live data is not affected.')) return
    await api.reset()
    setResetKey((k) => k + 1)
    setToast('Demo restored to its original state.')
    setTimeout(() => setToast(null), 3000)
  }

  const labels = info?.labels || {}
  return (
    <ModeCtx.Provider value={{ mode, setMode, info }}>
      <ResetCtx.Provider value={resetKey}>
        <EvidenceProvider>
          <div className="min-h-full flex flex-col">
            <header className="sticky top-0 z-40 bg-navy-900/95 backdrop-blur border-b border-navy-600">
              <div className="flex flex-wrap items-center gap-3 px-4 py-2">
                <button onClick={() => nav('/')} className="flex items-center gap-2" title="Back to landing">
                  <div className="h-7 w-7 rounded-md bg-cyan-500/20 border border-cyan-400/50 grid place-items-center text-cyan-300 text-xs font-bold">CG</div>
                  <span className="font-semibold text-white">CaseGraph</span>
                </button>
                <span className="px-2.5 py-1 rounded-md bg-amber-400 text-navy-950 text-xs font-bold tracking-wider" data-testid="demo-badge">DEMO MODE</span>
                <span className="hidden md:inline text-xs text-amber-300/90">Synthetic data — not a real investigation</span>
                <div className="ml-auto flex flex-wrap items-center gap-2">
                  <label className="text-xs text-slate-400 flex items-center gap-2" data-tour="mode-selector">
                    AI mode
                    <select className="input py-1" value={mode} onChange={(e) => setMode(e.target.value)} data-testid="mode-select">
                      {['precomputed', 'local', 'cloud'].map((m) => (
                        <option key={m} value={m} disabled={info && !info.available[m]}>
                          {m === 'precomputed' ? 'Precomputed' : m === 'local' ? 'Local (Ollama)' : 'Cloud'}{info && !info.available[m] ? ' — not configured' : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button className="btn" onClick={() => setTour(true)} data-testid="start-tour">Guided tour</button>
                  <button className="btn btn-danger" onClick={doReset} data-testid="reset">Reset demo</button>
                </div>
              </div>
              <nav className="flex gap-1 px-3 overflow-x-auto">
                {NAV.map(([to, label]) => (
                  <NavLink key={to} to={to ? `/demo/${to}` : '/demo'} end={!to}
                    className={({ isActive }) => `px-3 py-2 text-sm whitespace-nowrap border-b-2 transition-colors ${isActive ? 'border-cyan-400 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
                    {label}
                  </NavLink>
                ))}
              </nav>
              <div className="px-4 py-1.5 bg-navy-950 text-[11px] text-slate-400 border-t border-navy-700 flex flex-wrap gap-x-4">
                <span>Execution mode: <b className="text-cyan-300">{labels[mode] || mode}</b></span>
                {mode === 'precomputed' && <span>Seeded and rule-based results are never presented as newly generated AI analysis.</span>}
              </div>
            </header>
            <main className="flex-1 p-4 md:p-6 max-w-[1500px] w-full mx-auto" key={resetKey}><Outlet /></main>
            <footer className="px-4 py-3 text-center text-[11px] text-amber-300/70 border-t border-navy-700">SYNTHETIC DEMONSTRATION DATA – NOT A REAL INVESTIGATION</footer>
          </div>
          {tour && <Tour onClose={() => setTour(false)} />}
          {toast && <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 card px-4 py-2 text-sm fade-in">{toast}</div>}
        </EvidenceProvider>
      </ResetCtx.Provider>
    </ModeCtx.Provider>
  )
}

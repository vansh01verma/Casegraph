import React from 'react'
import { Link } from 'react-router-dom'

const Feature = ({ children }) => (
  <li className="flex gap-2 text-sm text-slate-300"><span className="text-cyan-400">▸</span>{children}</li>
)

export default function Landing({ liveHref = '/live', demoHref = '/demo' }) {
  return (
    <div className="min-h-full bg-gradient-to-b from-navy-950 via-navy-900 to-char-900 relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: 'radial-gradient(#4fd8f2 1px, transparent 1px)', backgroundSize: '28px 28px' }} />
      <div className="relative max-w-5xl mx-auto px-6 py-16">
        <div className="flex items-center gap-3 mb-10">
          <div className="h-9 w-9 rounded-lg bg-cyan-500/20 border border-cyan-400/50 grid place-items-center text-cyan-300 font-bold">CG</div>
          <span className="text-lg font-semibold tracking-tight text-white">CaseGraph</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-semibold text-white tracking-tight max-w-3xl">Digital evidence correlation &amp; crime reconstruction engine</h1>
        <p className="mt-4 text-slate-400 max-w-2xl">Correlate calls, chats, locations, CCTV, device logs and bank records into one verifiable picture — with every claim tied back to a hashed source record.</p>

        <div className="grid md:grid-cols-2 gap-5 mt-12">
          <Link to={liveHref} className="card p-6 hover:border-cyan-400/60 transition-colors group" data-testid="option-live">
            <div className="text-xs uppercase tracking-widest text-slate-500">Option A</div>
            <h2 className="text-xl font-semibold text-white mt-1">Live Investigation</h2>
            <ul className="mt-4 space-y-2">
              <Feature>Create new cases</Feature><Feature>Upload real evidence</Feature>
              <Feature>Run evidence processing</Feature><Feature>Use your configured AI models</Feature><Feature>Generate actual investigation reports</Feature>
            </ul>
            <div className="mt-6 text-sm text-cyan-300 group-hover:translate-x-1 transition-transform">Sign in to continue →</div>
          </Link>

          <Link to={demoHref} className="card p-6 border-cyan-500/50 bg-gradient-to-br from-cyan-500/10 to-navy-800 hover:border-cyan-300 transition-colors group" data-testid="option-demo">
            <div className="text-xs uppercase tracking-widest text-cyan-300/80">Option B</div>
            <h2 className="text-xl font-semibold text-white mt-1">Explore Demo Case</h2>
            <ul className="mt-4 space-y-2">
              <Feature>Opens instantly — no registration</Feature><Feature>No API key required</Feature>
              <Feature>Preloaded synthetic fraud investigation (≈240 records)</Feature><Feature>Every feature available, read-only to live data</Feature>
            </ul>
            <div className="mt-6 text-sm text-cyan-300 group-hover:translate-x-1 transition-transform">Explore the demo →</div>
          </Link>
        </div>
        <p className="mt-10 text-xs text-slate-500 max-w-2xl">All demo people, numbers, accounts and places are fictional. Demo Mode stores its data separately from live investigations and can be reset at any time.</p>
      </div>
    </div>
  )
}

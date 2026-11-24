import React from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Landing from './Landing.jsx'
import DemoLayout from './demo/DemoLayout.jsx'
import Dashboard from './demo/pages/Dashboard.jsx'
import Vault from './demo/pages/Vault.jsx'
import People from './demo/pages/People.jsx'
import Identity from './demo/pages/Identity.jsx'
import GraphPage from './demo/pages/GraphPage.jsx'
import Timeline from './demo/pages/Timeline.jsx'
import Contradictions from './demo/pages/Contradictions.jsx'
import Reconstruction from './demo/pages/Reconstruction.jsx'
import Gaps from './demo/pages/Gaps.jsx'
import Assistant from './demo/pages/Assistant.jsx'
import Report from './demo/pages/Report.jsx'

/** In the real CaseGraph app, "/live" is your existing application. This stub exists only so the standalone demo host has a target. */
function LivePlaceholder() {
  return (
    <div className="min-h-full grid place-items-center p-8">
      <div className="card p-8 max-w-lg text-center">
        <h1 className="text-xl font-semibold text-white">Live Investigation</h1>
        <p className="text-slate-400 mt-3 text-sm">This route is a placeholder in the standalone demo host. In CaseGraph, point the landing page's “Live Investigation” option at your existing authenticated application.</p>
        <Link to="/" className="btn mt-5">Back to landing</Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing liveHref="/live" demoHref="/demo" />} />
      <Route path="/live" element={<LivePlaceholder />} />
      <Route path="/demo" element={<DemoLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="vault" element={<Vault />} />
        <Route path="people" element={<People />} />
        <Route path="identity" element={<Identity />} />
        <Route path="graph" element={<GraphPage />} />
        <Route path="timeline" element={<Timeline />} />
        <Route path="contradictions" element={<Contradictions />} />
        <Route path="reconstruction" element={<Reconstruction />} />
        <Route path="gaps" element={<Gaps />} />
        <Route path="assistant" element={<Assistant />} />
        <Route path="report" element={<Report />} />
      </Route>
    </Routes>
  )
}

import React from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, fmtDateTime } from '../../api'
import { Badge, EvChips, Loading, PageHeader, SyntheticTag, useAsync } from '../ui.jsx'

const COLORS = ['#22d3ee', '#3b82f6', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#94a3b8']
const Metric = ({ label, value, sub, tone }) => (
  <div className="card p-4"><div className="text-xs text-slate-400">{label}</div>
    <div className={`text-3xl font-semibold mt-1 ${tone || 'text-white'}`}>{value}</div>{sub && <div className="text-[11px] text-slate-500 mt-1">{sub}</div>}</div>
)

export default function Dashboard() {
  const st = useAsync(() => Promise.all([api.overview(), api.caseInfo()]), [])
  if (st.loading || st.error) return <Loading state={st} />
  const [o, c] = st.data
  const m = o.metrics
  const pct = Math.round(o.progress.overall * 100)
  return (
    <div className="fade-in">
      <PageHeader title={c.title} subtitle={c.summary}><SyntheticTag /><Badge tone="cyan">{c.status}</Badge></PageHeader>
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3" data-tour="dashboard-metrics">
        <Metric label="Evidence records" value={m.evidence_records} />
        <Metric label="People" value={m.people} />
        <Metric label="Devices" value={m.devices} />
        <Metric label="Transactions" value={m.transactions} />
        <Metric label="Contradictions" value={m.contradictions_detected} sub={`${m.contradictions_open} awaiting review`} tone="text-amber-300" />
        <Metric label="Unresolved gaps" value={m.gaps_unresolved} sub={`of ${m.gaps_total}`} tone="text-red-300" />
        <Metric label="Progress" value={`${pct}%`} sub="review-based" tone="text-cyan-300" />
      </div>
      <div className="grid lg:grid-cols-3 gap-4 mt-4">
        <div className="card p-4"><h3 className="text-sm font-medium text-white mb-2">Evidence by category</h3>
          <div className="h-56"><ResponsiveContainer><PieChart><Pie data={o.categories} dataKey="count" nameKey="label" innerRadius={45} outerRadius={80} paddingAngle={2}>
            {o.categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />)}</Pie>
            <Tooltip contentStyle={{ background: '#08142a', border: '1px solid #1b3553', borderRadius: 8 }} /></PieChart></ResponsiveContainer></div>
          <div className="flex flex-wrap gap-x-3 gap-y-1">{o.categories.map((c2, i) => <span key={c2.key} className="text-[11px] text-slate-300 flex items-center gap-1"><i className="h-2 w-2 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />{c2.label} ({c2.count})</span>)}</div></div>
        <div className="card p-4"><h3 className="text-sm font-medium text-white mb-2">Activity on 14 March (records per hour)</h3>
          <div className="h-56"><ResponsiveContainer><BarChart data={o.hourly_activity}><CartesianGrid stroke="#1b3553" vertical={false} />
            <XAxis dataKey="hour" stroke="#64748b" fontSize={11} /><YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
            <Tooltip contentStyle={{ background: '#08142a', border: '1px solid #1b3553', borderRadius: 8 }} cursor={{ fill: '#12263f' }} />
            <Bar dataKey="records" fill="#22d3ee" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></div>
        <div className="card p-4"><h3 className="text-sm font-medium text-white mb-3">Investigation progress</h3>
          <div className="h-2 bg-navy-900 rounded-full overflow-hidden mb-4"><div className="h-full bg-cyan-400 transition-all" style={{ width: `${pct}%` }} /></div>
          {Object.entries(o.progress.components).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-sm py-1"><span className="text-slate-300 capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="font-mono text-slate-200">{Math.round(v * 100)}%</span></div>))}
          <p className="text-[11px] text-slate-500 mt-2">Accept/reject identity matches and review contradictions to move progress.</p></div>
      </div>
      <div className="card p-4 mt-4"><h3 className="text-sm font-medium text-white mb-3">Recent investigation events</h3>
        <ul className="divide-y divide-navy-700">{o.recent_events.map((e, i) => (
          <li key={i} className="py-2 flex flex-wrap items-center gap-2 text-sm"><Badge tone={e.kind === 'contradiction' ? 'amber' : e.kind === 'identity' ? 'violet' : e.kind === 'user_action' ? 'green' : 'cyan'}>{e.kind.replace('_', ' ')}</Badge>
            <span className="text-slate-200">{e.text}</span><EvChips ids={e.evidence_ids.slice(0, 4)} /><span className="ml-auto text-[11px] font-mono text-slate-500">{fmtDateTime(e.ts)}</span></li>))}</ul></div>
      <div className="mt-4 text-sm text-slate-400">Next: <Link className="text-cyan-300 hover:underline" to="/demo/vault">inspect the evidence</Link> or <Link className="text-cyan-300 hover:underline" to="/demo/contradictions">review the contradictions</Link>.</div>
    </div>
  )
}

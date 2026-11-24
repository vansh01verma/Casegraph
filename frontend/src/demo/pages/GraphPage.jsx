import React, { useCallback, useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow'
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from 'd3-force'
import { api } from '../../api'
import { Badge, ConfidenceBar, EvChips, Loading, PageHeader, SyntheticTag, useAsync } from '../ui.jsx'

const TYPE_STYLE = {
  person: '#22d3ee', device: '#60a5fa', phone: '#818cf8', location: '#34d399', account: '#f59e0b',
  transaction: '#f472b6', event: '#f87171', alias: '#a78bfa',
}
const SHOW_BY_DEFAULT = ['person', 'device', 'phone', 'location', 'account', 'transaction', 'event', 'alias']

function layout(nodes, edges) {
  const sim = nodes.map((n, i) => ({ id: n.id, x: 450 + 300 * Math.cos(i * 2.4), y: 300 + 220 * Math.sin(i * 2.4) }))
  const idx = new Map(sim.map((n) => [n.id, n]))
  const links = edges.filter((e) => idx.has(e.source) && idx.has(e.target)).map((e) => ({ source: e.source, target: e.target }))
  const s = forceSimulation(sim).force('link', forceLink(links).id((d) => d.id).distance(160))
    .force('charge', forceManyBody().strength(-520)).force('x', forceX(450).strength(0.09)).force('y', forceY(300).strength(0.12)).force('collide', forceCollide(70)).stop()
  for (let i = 0; i < 220; i++) s.tick()
  return idx
}

export default function GraphPage() {
  const st = useAsync(() => api.graph(), [])
  const [types, setTypes] = useState(new Set(SHOW_BY_DEFAULT))
  const [search, setSearch] = useState('')
  const [sel, setSel] = useState(null)
  const [focus, setFocus] = useState(null)         // expanded neighbourhood root
  const [selEdge, setSelEdge] = useState(null)
  const [detail, setDetail] = useState(null)

  const data = st.data
  const pos = useMemo(() => (data ? layout(data.nodes, data.edges) : null), [data])
  const visibleIds = useMemo(() => {
    if (!data) return new Set()
    let ids = new Set(data.nodes.filter((n) => types.has(n.type)).map((n) => n.id))
    if (focus) {
      const nb = new Set([focus])
      data.edges.forEach((e) => { if (e.source === focus) nb.add(e.target); if (e.target === focus) nb.add(e.source) })
      ids = new Set([...ids].filter((i) => nb.has(i)))
    }
    return ids
  }, [data, types, focus])

  useEffect(() => { if (sel) api.entity(sel).then(setDetail).catch(() => setDetail(null)); else setDetail(null) }, [sel])

  const matches = useMemo(() => {
    if (!data || !search.trim()) return new Set()
    const q = search.toLowerCase()
    return new Set(data.nodes.filter((n) => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)).map((n) => n.id))
  }, [data, search])

  const rfNodes = useMemo(() => (data ? data.nodes.filter((n) => visibleIds.has(n.id)).map((n) => ({
    id: n.id, position: { x: pos.get(n.id).x, y: pos.get(n.id).y }, data: { label: n.label.length > 26 ? n.label.slice(0, 25) + '…' : n.label },
    style: {
      background: '#08142a', color: '#e2e8f0', border: `2px solid ${TYPE_STYLE[n.type] || '#94a3b8'}`, borderRadius: n.type === 'person' ? 24 : 8,
      fontSize: 11, padding: '6px 10px', width: 170, textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', boxShadow: n.id === sel ? `0 0 0 3px ${TYPE_STYLE[n.type]}66` : matches.has(n.id) ? '0 0 0 3px #fde04799' : 'none',
      opacity: matches.size && !matches.has(n.id) ? 0.35 : 1,
    },
  })) : []), [data, visibleIds, pos, sel, matches])

  const rfEdges = useMemo(() => (data ? data.edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target)).map((e) => ({
    id: e.id, source: e.source, target: e.target, label: e.kind === 'possible_same_identity' ? `possible same · ${e.confidence}` : undefined,
    animated: e.kind === 'possible_same_identity', markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
    style: { stroke: e.kind === 'possible_same_identity' ? '#a78bfa' : e.id === selEdge?.id ? '#22d3ee' : '#475569', strokeWidth: 1 + e.confidence * 1.5, strokeDasharray: e.kind === 'possible_same_identity' ? '6 4' : undefined },
    labelStyle: { fill: '#c4b5fd', fontSize: 10 }, labelBgStyle: { fill: '#08142a' },
  })) : []), [data, visibleIds, selEdge])

  const toggle = (t) => setTypes((s) => { const n = new Set(s); n.has(t) ? n.delete(t) : n.add(t); return n })
  const onNode = useCallback((_, n) => { setSel(n.id); setSelEdge(null) }, [])
  const onEdge = useCallback((_, e) => setSelEdge(data.edges.find((x) => x.id === e.id)), [data])
  if (st.loading || st.error) return <Loading state={st} />

  const nodeById = Object.fromEntries(data.nodes.map((n) => [n.id, n]))
  const nodeEdges = sel ? data.edges.filter((e) => e.source === sel || e.target === sel) : []

  return (
    <div className="fade-in">
      <PageHeader title="Knowledge Graph" subtitle="People, devices, numbers, places, accounts, transactions and events. Click a node for details, “Expand” to focus on its connections, or click an edge to see its evidence and confidence."><SyntheticTag /></PageHeader>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <input className="input w-64" placeholder="Search entities…" value={search} onChange={(e) => setSearch(e.target.value)} data-testid="graph-search" />
        {matches.size > 0 && <span className="text-xs text-amber-300">{matches.size} match(es) highlighted</span>}
        {Object.keys(TYPE_STYLE).filter((t) => data.types.includes(t)).map((t) => (
          <button key={t} onClick={() => toggle(t)} data-testid={`filter-${t}`}
            className={`px-2.5 py-1 rounded-full text-xs border transition-opacity ${types.has(t) ? '' : 'opacity-40'}`} style={{ borderColor: TYPE_STYLE[t], color: TYPE_STYLE[t] }}>{t}</button>))}
        {focus && <button className="btn" onClick={() => setFocus(null)}>Show full graph</button>}
        <span className="text-xs text-slate-500 ml-auto" data-testid="graph-counts">{rfNodes.length} nodes · {rfEdges.length} edges</span>
      </div>
      <div className="grid lg:grid-cols-[1fr_340px] gap-4">
        <div className="card h-[620px] overflow-hidden" data-tour="graph-canvas" data-testid="graph-canvas">
          <ReactFlow nodes={rfNodes} edges={rfEdges} onNodeClick={onNode} onEdgeClick={onEdge} fitView fitViewOptions={{ padding: 0.12 }} onInit={(inst) => { setTimeout(() => inst.fitView({ padding: 0.12 }), 80); setTimeout(() => inst.fitView({ padding: 0.12 }), 400) }} minZoom={0.2} proOptions={{ hideAttribution: true }}
            nodesConnectable={false} key={`${focus}-${[...types].join()}`}>
            <Background color="#1b3553" gap={24} /><Controls showInteractive={false} />
          </ReactFlow>
        </div>
        <aside className="card p-4 h-[620px] overflow-y-auto" data-testid="graph-detail">
          {!sel && !selEdge && <p className="text-sm text-slate-400">Select a node or relationship. Dashed purple edges are <i>proposed</i> identity matches, not established facts.</p>}
          {selEdge && (
            <div className="mb-4 pb-4 border-b border-navy-600">
              <Badge tone="violet">relationship</Badge>
              <h3 className="text-white mt-2 text-sm">{nodeById[selEdge.source]?.label} <span className="text-slate-500">→ {selEdge.kind.replace(/_/g, ' ')} →</span> {nodeById[selEdge.target]?.label}</h3>
              <div className="mt-2"><ConfidenceBar value={selEdge.confidence} /></div>
              <p className="text-xs text-slate-300 mt-2">{selEdge.note}</p>
              <div className="mt-2 text-xs text-slate-400 flex flex-wrap gap-1 items-center">Supporting evidence: {selEdge.evidence_ids.length ? <EvChips ids={selEdge.evidence_ids} /> : 'none (registration/structural link)'}</div>
            </div>)}
          {sel && nodeById[sel] && (
            <div>
              <Badge tone="cyan">{nodeById[sel].type}</Badge>
              <h3 className="text-white font-medium mt-2">{nodeById[sel].label}</h3>
              {nodeById[sel].role && <p className="text-xs text-slate-400 mt-1">{nodeById[sel].role}</p>}
              <div className="flex gap-2 mt-3"><button className="btn" onClick={() => setFocus(sel)} data-testid="expand">Expand connections</button><button className="btn" onClick={() => { setSel(null); setFocus(null) }}>Clear</button></div>
              <h4 className="text-xs text-slate-400 mt-4 mb-1">Relationships ({nodeEdges.length})</h4>
              <ul className="space-y-1.5">{nodeEdges.map((e) => { const other = e.source === sel ? e.target : e.source; return (
                <li key={e.id} className="text-xs"><button className="text-left hover:text-cyan-300" onClick={() => setSelEdge(e)}>
                  <span className="text-slate-400">{e.source === sel ? '→' : '←'} {e.kind.replace(/_/g, ' ')}</span> <span className="text-slate-200">{nodeById[other]?.label}</span> <span className="font-mono text-slate-500">{e.confidence}</span></button></li>) })}</ul>
              {detail?.evidence?.length > 0 && (<><h4 className="text-xs text-slate-400 mt-4 mb-1">Supporting evidence ({detail.evidence_count})</h4>
                <div className="flex flex-wrap gap-1">{detail.evidence.slice(0, 20).map((e) => <EvChips key={e.id} ids={[e.id]} />)}</div></>)}
            </div>)}
        </aside>
      </div>
    </div>
  )
}

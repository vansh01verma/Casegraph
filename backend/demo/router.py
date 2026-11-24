"""FastAPI router for Demo Mode. Mount with ``app.include_router(demo_router)``.

* No authentication dependency: Demo Mode is open by design.
* No live-database dependency: every handler uses ONLY the dedicated demo engine.
* Demo files are served only from the demo files directory.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import analytics, assistant, config, llm, queries, reconstruction, report as report_svc, seed as seed_mod
from .db import demo_session, get_engine
from .models import (DemoContradiction, DemoEntity, DemoEvidence, DemoHypothesis, DemoIdentityMatch)

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _ensure_seeded():
    get_engine()
    with demo_session() as s:
        empty = s.query(DemoEvidence).count() == 0
    if empty:
        seed_mod.seed()


def _guard():
    """Called by every endpoint: lazily seeds the demo database on first use."""
    _ensure_seeded()


def _dt(v):
    return datetime.fromisoformat(v) if v else None


class AssistantIn(BaseModel):
    question: str
    mode: str | None = None


class ModeIn(BaseModel):
    mode: str | None = None


class DecisionIn(BaseModel):
    decision: str   # accept | reject | reset


class ReviewIn(BaseModel):
    status: str     # confirmed_conflict | dismissed | needs_review


@router.get("/mode")
def mode(requested: str | None = None):
    return llm.describe_modes(requested)


@router.get("/overview")
def overview():
    _guard()
    with demo_session() as s:
        return queries.overview(s)


@router.get("/case")
def case():
    _guard()
    with demo_session() as s:
        return queries.case_payload(s)


@router.get("/evidence")
def evidence(category: str | None = None, q: str | None = None, person: str | None = None, status: str | None = None,
             start: str | None = None, end: str | None = None, limit: int = Query(50, le=300), offset: int = 0):
    _guard()
    with demo_session() as s:
        return queries.list_evidence(s, category, q, person, status, _dt(start), _dt(end), limit, offset)


@router.get("/evidence/{evidence_id}")
def evidence_detail(evidence_id: str):
    _guard()
    with demo_session() as s:
        d = queries.evidence_detail(s, evidence_id)
        if not d:
            raise HTTPException(404, "Evidence not found in the demo dataset")
        return d


@router.get("/evidence/{evidence_id}/verify")
def verify(evidence_id: str):
    """Recompute the SHA-256 and compare with the stored value."""
    _guard()
    import hashlib
    with demo_session() as s:
        ev = s.get(DemoEvidence, evidence_id)
        if not ev:
            raise HTTPException(404, "Evidence not found in the demo dataset")
        if ev.file_path:
            actual = hashlib.sha256((config.DEMO_ROOT / ev.file_path).read_bytes()).hexdigest()
        else:
            actual = seed_mod.canonical_hash({"category": ev.category, "source_device": ev.source_device,
                                              "original_ts": ev.original_ts, "content": ev.content})
        queries.audit(s, "evidence_verify", {"id": evidence_id, "match": actual == ev.sha256})
        return {"id": ev.id, "stored_sha256": ev.sha256, "recomputed_sha256": actual, "match": actual == ev.sha256}


@router.get("/files/{evidence_id}")
def files(evidence_id: str):
    _guard()
    with demo_session() as s:
        ev = s.get(DemoEvidence, evidence_id)
        if not ev or not ev.file_path:
            raise HTTPException(404, "No demo file for this record")
        path = (config.DEMO_ROOT / ev.file_path).resolve()
        if config.DEMO_FILES_DIR.resolve() not in path.parents:
            raise HTTPException(403, "Outside the demo files directory")
        return FileResponse(path, media_type="image/png")


@router.get("/entities")
def entities(type: str | None = None):
    _guard()
    with demo_session() as s:
        q = s.query(DemoEntity)
        if type:
            q = q.filter(DemoEntity.type.in_(type.split(",")))
        return {"items": [{"id": e.id, "type": e.type, "label": e.label, "role": e.role, "attrs": e.attrs, "synthetic": True}
                          for e in q.order_by(DemoEntity.type, DemoEntity.id)]}


@router.get("/entities/{entity_id}")
def entity(entity_id: str):
    _guard()
    with demo_session() as s:
        d = queries.entity_profile(s, entity_id)
        if not d:
            raise HTTPException(404, "Entity not found in the demo dataset")
        return d


@router.get("/identity")
def identity():
    _guard()
    with demo_session() as s:
        return {"items": [queries.ser_match(m, s) for m in s.query(DemoIdentityMatch).order_by(DemoIdentityMatch.id)]}


@router.post("/identity/{match_id}/decision")
def identity_decision(match_id: str, body: DecisionIn):
    _guard()
    if body.decision not in ("accept", "reject", "reset"):
        raise HTTPException(422, "decision must be accept, reject or reset")
    with demo_session() as s:
        m = s.get(DemoIdentityMatch, match_id)
        if not m:
            raise HTTPException(404, "Identity match not found")
        old = m.status
        m.status = {"accept": "accepted", "reject": "rejected", "reset": "proposed"}[body.decision]
        queries.audit(s, "identity_decision", {"match": match_id, "from": old, "to": m.status})
        return queries.ser_match(m, s)


@router.get("/graph")
def graph(types: str | None = None):
    _guard()
    with demo_session() as s:
        g = analytics.build_graph(s)
        keep = set(types.split(",")) if types else None
        nodes = [{"id": n, **{k: v for k, v in d.items()}, "degree": g.degree(n)} for n, d in g.nodes(data=True)
                 if not keep or d["type"] in keep]
        ids = {n["id"] for n in nodes}
        edges = [{"id": d["id"], "source": u, "target": v, "kind": d["kind"], "confidence": d["confidence"],
                  "evidence_ids": d["evidence_ids"], "note": d["note"], "status": d["status"]}
                 for u, v, d in g.edges(data=True) if u in ids and v in ids]
        return {"nodes": nodes, "edges": edges, "synthetic": True,
                "types": sorted({n["type"] for n in nodes})}


@router.get("/graph/neighbors/{node_id}")
def neighbors(node_id: str):
    _guard()
    with demo_session() as s:
        g = analytics.build_graph(s)
        if node_id not in g:
            raise HTTPException(404, "Node not found in the demo graph")
        ids = {node_id} | set(g.predecessors(node_id)) | set(g.successors(node_id))
        return {"nodes": [{"id": n, **g.nodes[n], "degree": g.degree(n)} for n in ids],
                "edges": [{"id": d["id"], "source": u, "target": v, "kind": d["kind"], "confidence": d["confidence"],
                           "evidence_ids": d["evidence_ids"], "note": d["note"], "status": d["status"]}
                          for u, v, d in g.edges(data=True) if u in ids and v in ids and node_id in (u, v)]}


@router.get("/timeline")
def timeline(types: str | None = None, persons: str | None = None, start: str | None = None, end: str | None = None,
             scope: str = "incident"):
    _guard()
    with demo_session() as s:
        return queries.timeline(s, types.split(",") if types else None, persons.split(",") if persons else None,
                                _dt(start), _dt(end), scope)


@router.get("/contradictions")
def contradictions():
    _guard()
    with demo_session() as s:
        return {"items": [queries.ser_contradiction(c) for c in s.query(DemoContradiction).order_by(DemoContradiction.id)]}


@router.post("/contradictions/{cid}/review")
def review(cid: str, body: ReviewIn):
    _guard()
    if body.status not in ("needs_review", "confirmed_conflict", "dismissed"):
        raise HTTPException(422, "invalid status")
    with demo_session() as s:
        c = s.get(DemoContradiction, cid)
        if not c:
            raise HTTPException(404, "Contradiction not found")
        queries.audit(s, "contradiction_review", {"id": cid, "from": c.review_status, "to": body.status})
        c.review_status = body.status
        return queries.ser_contradiction(c)


@router.get("/hypotheses")
def hypotheses():
    _guard()
    with demo_session() as s:
        return {"items": [queries.ser_hypothesis(h) for h in s.query(DemoHypothesis).order_by(DemoHypothesis.id)],
                "produced_by": reconstruction.SEEDED, "mode_label": llm.MODE_LABELS["precomputed"]}


@router.post("/hypotheses/{hid}/challenge")
def challenge(hid: str):
    """Run the critic on one scenario (seeded challenges + rule-based checks)."""
    _guard()
    with demo_session() as s:
        h = s.get(DemoHypothesis, hid)
        if not h:
            raise HTTPException(404, "Scenario not found")
        d = queries.ser_hypothesis(h)
        queries.audit(s, "scenario_challenge", {"id": hid})
        return {"scenario": d["id"], "critic": d["critic"], "automatic_checks": reconstruction._auto_checks(s, [d]),
                "produced_by": reconstruction.SEEDED + " + rule-based checks"}


@router.get("/gaps")
def gaps():
    _guard()
    with demo_session() as s:
        return queries.gaps_payload(s)


@router.post("/assistant")
def assistant_ask(body: AssistantIn):
    _guard()
    if not body.question.strip():
        raise HTTPException(422, "question is required")
    with demo_session() as s:
        res = assistant.ask(s, body.question, body.mode)
        queries.audit(s, "assistant_question", {"q": body.question[:200], "intent": res["intent"], "mode": res["mode_used"]})
        return res


@router.post("/reconstruction/run")
def reconstruction_run(body: ModeIn | None = None):
    _guard()
    with demo_session() as s:
        res = reconstruction.run(s, body.mode if body else None)
        queries.audit(s, "reconstruction_run", {"mode_used": res["mode_used"]})
        return res


@router.post("/report/generate")
def report_generate():
    _guard()
    with demo_session() as s:
        data, meta = report_svc.build_report(s)
        report_svc.save_report(data, meta)
        queries.audit(s, "report_generate", {"report_id": meta["report_id"], "sha256": meta["sha256"]})
        return {**meta, "download_url": f"/api/demo/report/{meta['report_id']}/download"}


@router.get("/report/{report_id}/download")
def report_download(report_id: str):
    _guard()
    path = (config.DEMO_REPORTS_DIR / f"{report_id}.pdf").resolve()
    if config.DEMO_REPORTS_DIR.resolve() not in path.parents or not path.exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="application/pdf", filename=f"CaseGraph-DEMO-report-{report_id}.pdf")


@router.get("/audit")
def audit(limit: int = 100):
    _guard()
    with demo_session() as s:
        return {"items": queries.audit_log(s, limit)}


@router.post("/reset")
def reset():
    """Restore the original demo state. Touches only demo_* tables and demo files."""
    _guard()
    result = seed_mod.seed(preserve_audit=True)
    with demo_session() as s:
        queries.audit(s, "reset", {"records": result["evidence"]})
    return {"status": "reset", "evidence": result["evidence"], "message": "Demo restored to its original state."}

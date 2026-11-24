"""Demo-specific database queries and serializers (all read from demo_* tables)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import analytics, config, dataset as ds
from .models import (DemoAudit, DemoCase, DemoContradiction, DemoCustody, DemoEntity, DemoEvidence, DemoGap,
                     DemoHypothesis, DemoIdentityMatch)

CATEGORY_LABEL = {"cdr": "Call records (CDR)", "whatsapp": "WhatsApp chats", "gps": "GPS / location",
                  "transaction": "Bank & UPI transactions", "cctv": "CCTV", "statement": "Statements",
                  "device_log": "Device logs"}

_PERSON_NAME = {p: n for p, n, _ in ds.PEOPLE}


def person_label(pid: str) -> str:
    return f"{_PERSON_NAME[pid]} (Person {pid[-1]})" if pid in _PERSON_NAME else pid


def phone_name(pid: str) -> str:
    num, owner = ds.PHONES[pid]
    return f"{_PERSON_NAME[owner].split()[0]} ({num})" if owner else f"{num} (unregistered)"


def account_label(a: str) -> str:
    if a in ds.ACCOUNTS:
        return ds.ACCOUNTS[a][0]
    if a in ds.UPI:
        return f"UPI {ds.UPI[a][0]}"
    return a.replace("INV-PAYER-", "Investor payer #")


def summarize(ev: DemoEvidence) -> str:
    c = ev.content
    if ev.category == "cdr":
        return f"{phone_name(c['caller_id'])} called {phone_name(c['callee_id'])} for {c['duration_s']}s via {c['tower']}"
    if ev.category == "whatsapp":
        return f"{phone_name(c['sender_id'])} → {c['recipient'] if c['recipient'] == ds.TEAM_CHAT else c['recipient']}: “{c['text']}”"
    if ev.category == "gps":
        return f"{c['device']} located near {c['place']} (±{c['accuracy_m']} m)"
    if ev.category == "transaction":
        return f"₹{ds.inr(c['amount_inr'])} via {c['channel']}: {account_label(c['from_account'])} → {account_label(c['to_account'])}"
    if ev.category == "cctv":
        return c["description"]
    if ev.category == "statement":
        t = c["text"]
        return f"{c['witness']}: “{t[:150]}{'…' if len(t) > 150 else ''}”"
    return f"{c['device']}: {c['message']}"


def ser_evidence(ev: DemoEvidence, detail: bool = False) -> dict:
    d = {"id": ev.id, "category": ev.category, "category_label": CATEGORY_LABEL[ev.category], "title": ev.title,
         "summary": summarize(ev), "source": ev.source_device, "original_ts": ev.original_ts.isoformat(),
         "corrected_ts": ev.corrected_ts.isoformat(), "clock_offset_seconds": ev.clock_offset_seconds,
         "timestamp_corrected": ev.clock_offset_seconds != 0, "sha256": ev.sha256,
         "processing_status": ev.processing_status, "persons": ev.persons or [],
         "event_time": analytics.event_time(ev).isoformat(), "synthetic": True,
         "label": config.SYNTHETIC_LABEL, "has_file": bool(ev.file_path)}
    if detail:
        d["content"] = ev.content
        d["file_url"] = f"/api/demo/files/{ev.id}" if ev.file_path else None
    return d


def list_evidence(s: Session, category=None, q=None, person=None, status=None, start=None, end=None,
                  limit=50, offset=0) -> dict:
    qs = s.query(DemoEvidence)
    if category:
        qs = qs.filter(DemoEvidence.category.in_(category.split(",")))
    if status:
        qs = qs.filter(DemoEvidence.processing_status == status)
    rows = qs.order_by(DemoEvidence.id).all()
    if person:
        rows = [r for r in rows if person in (r.persons or [])]
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.id.lower() or ql in summarize(r).lower() or ql in r.title.lower()
                or ql in r.sha256 or ql in str(r.content).lower()]
    if start:
        rows = [r for r in rows if analytics.event_time(r) >= start]
    if end:
        rows = [r for r in rows if analytics.event_time(r) <= end]
    total = len(rows)
    counts = Counter(r.category for r in s.query(DemoEvidence))
    return {"total": total, "items": [ser_evidence(r) for r in rows[offset:offset + limit]],
            "categories": [{"key": k, "label": CATEGORY_LABEL[k], "count": v} for k, v in sorted(counts.items())]}


def evidence_detail(s: Session, eid: str) -> dict | None:
    ev = s.get(DemoEvidence, eid)
    if not ev:
        return None
    d = ser_evidence(ev, True)
    d["custody"] = [{"ts": c.ts.isoformat(), "action": c.action, "actor": c.actor, "note": c.note}
                    for c in s.query(DemoCustody).filter_by(evidence_id=eid).order_by(DemoCustody.ts)]
    d["cited_in"] = {
        "contradictions": [c.id for c in s.query(DemoContradiction)
                           if eid in (c.conflicting_evidence_ids or []) + (c.supporting_evidence_ids or [])
                           + [c.statement_evidence_id]],
        "hypotheses": [h.id for h in s.query(DemoHypothesis)
                       if eid in [x["evidence_id"] for x in (h.supporting or []) + (h.contradicting or [])]],
    }
    return d


# ---------------------------------------------------------------- timeline
def timeline(s: Session, types=None, persons=None, start=None, end=None, scope="incident") -> dict:
    rows = s.query(DemoEvidence).all()
    if scope == "incident" and not (start or end):
        start, end = datetime(2026, 3, 14, 20, 0), datetime(2026, 3, 14, 23, 0)
    out = []
    for r in rows:
        t = analytics.event_time(r)
        if (start and t < start) or (end and t > end):
            continue
        if types and r.category not in types:
            continue
        if persons and not set(persons) & set(r.persons or []):
            continue
        d = ser_evidence(r)
        d["kind"] = "claim" if r.category == "statement" else "record"
        d["ts"] = t.isoformat()
        out.append(d)
    # derived analytical markers (not evidence)
    if not types or "analysis" in types:
        for e in s.query(DemoEntity).filter_by(type="event"):
            a = e.attrs or {}
            ts = a.get("start")
            if a.get("kind") == "clock_skew":
                ts = "2026-03-14T21:17:00"
            if ts and (not start or datetime.fromisoformat(ts) >= start) and (not end or datetime.fromisoformat(ts) <= end):
                if persons and not set(persons) & set(a.get("persons", [])):
                    continue
                out.append({"id": e.id, "category": "analysis", "category_label": "Analytical finding", "title": e.label,
                            "summary": e.label + " (computed from records)", "ts": ts, "kind": "finding", "persons": a.get("persons", []),
                            "evidence_ids": a.get("evidence_ids") or a.get("validated_by") or [], "synthetic": True,
                            "original_ts": ts, "corrected_ts": ts, "timestamp_corrected": False, "label": config.SYNTHETIC_LABEL})
    out.sort(key=lambda x: (x["ts"], x["id"]))
    span = (s.query(func.min(DemoEvidence.corrected_ts)).scalar(), s.query(func.max(DemoEvidence.corrected_ts)).scalar())
    return {"events": out, "count": len(out), "range": {"start": start.isoformat() if start else span[0].isoformat(),
                                                         "end": end.isoformat() if end else span[1].isoformat()}}


# ---------------------------------------------------------------- gaps / identity / contradictions
def gaps_payload(s: Session) -> dict:
    ms = {m.id: m for m in s.query(DemoIdentityMatch)}
    items = []
    for g in s.query(DemoGap).order_by(DemoGap.id):
        resolved = g.resolved
        if g.kind == "identity":
            resolved = ms[g.id.replace("GAP-ID-", "")].status != "proposed"
        items.append({"id": g.id, "kind": g.kind, "title": g.title, "detail": g.detail, "severity": g.severity,
                      "window_start": g.window_start.isoformat() if g.window_start else None,
                      "window_end": g.window_end.isoformat() if g.window_end else None,
                      "evidence_ids": g.evidence_ids or [], "next_steps": g.next_steps or [], "resolved": resolved})
    return {"items": items, "unresolved": sum(1 for i in items if not i["resolved"]), "total": len(items)}


def ser_match(m: DemoIdentityMatch, s: Session) -> dict:
    def lab(eid):
        e = s.get(DemoEntity, eid)
        return e.label if e else eid
    return {"id": m.id, "entity_a": m.entity_a, "entity_a_label": lab(m.entity_a), "entity_b": m.entity_b,
            "entity_b_label": lab(m.entity_b), "score": m.score, "features": m.features, "explanation": m.explanation,
            "evidence_ids": m.evidence_ids or [], "status": m.status, "synthetic": True}


def ser_contradiction(c: DemoContradiction) -> dict:
    return {"id": c.id, "title": c.title, "statement": c.statement, "statement_evidence_id": c.statement_evidence_id,
            "conflicting_evidence_ids": c.conflicting_evidence_ids, "supporting_evidence_ids": c.supporting_evidence_ids,
            "time_info": c.time_info, "explanation": c.explanation, "caveats": c.caveats, "confidence": c.confidence,
            "review_status": c.review_status, "synthetic": True}


def ser_hypothesis(h: DemoHypothesis) -> dict:
    return {"id": h.id, "title": h.title, "description": h.description, "supporting": h.supporting,
            "contradicting": h.contradicting, "confidence": h.confidence, "reasoning": h.reasoning,
            "missing": h.missing, "critic": h.critic, "synthetic": True}


# ---------------------------------------------------------------- overview
def overview(s: Session) -> dict:
    case = s.query(DemoCase).first()
    ev_total = s.query(DemoEvidence).count()
    cats = Counter(e.category for e in s.query(DemoEvidence))
    matches = s.query(DemoIdentityMatch).all()
    cons = s.query(DemoContradiction).all()
    gp = gaps_payload(s)
    hourly = Counter(analytics.event_time(e).strftime("%H:00") for e in s.query(DemoEvidence)
                     if e.corrected_ts.date() == datetime(2026, 3, 14).date() and e.category != "statement"
                     and 18 <= e.corrected_ts.hour <= 23)
    ident_rev = sum(1 for m in matches if m.status != "proposed")
    con_rev = sum(1 for c in cons if c.review_status != "needs_review")
    comps = {"evidence_processed": sum(1 for e in s.query(DemoEvidence) if e.processing_status == "processed") / ev_total,
             "identities_reviewed": ident_rev / len(matches), "contradictions_reviewed": con_rev / len(cons),
             "gaps_resolved": (gp["total"] - gp["unresolved"]) / gp["total"]}
    events = []
    for e in s.query(DemoEntity).filter_by(type="event"):
        events.append({"ts": "2026-03-16T12:00:00", "kind": "analysis", "text": f"Detected: {e.label}",
                       "evidence_ids": (e.attrs or {}).get("evidence_ids") or (e.attrs or {}).get("validated_by") or []})
    for c in cons:
        events.append({"ts": "2026-03-16T12:30:00", "kind": "contradiction", "text": f"{c.id}: {c.title}",
                       "evidence_ids": [c.statement_evidence_id] + (c.conflicting_evidence_ids or [])})
    for m in matches:
        events.append({"ts": "2026-03-16T12:45:00", "kind": "identity", "text": f"Identity match {m.id} proposed (score {m.score:.2f})",
                       "evidence_ids": m.evidence_ids or []})
    for a in s.query(DemoAudit).order_by(DemoAudit.ts.desc()).limit(8):
        if a.action in ("identity_decision", "contradiction_review", "reconstruction_run", "report_generate", "assistant_question"):
            events.append({"ts": a.ts.isoformat(), "kind": "user_action", "text": f"Demo action: {a.action.replace('_', ' ')}",
                           "evidence_ids": []})
    events.sort(key=lambda x: x["ts"], reverse=True)
    return {
        "case": {"id": case.id, "title": case.title, "status": case.status},
        "metrics": {"evidence_records": ev_total,
                    "people": s.query(DemoEntity).filter_by(type="person").count(),
                    "devices": s.query(DemoEntity).filter_by(type="device").count(),
                    "transactions": cats.get("transaction", 0),
                    "contradictions_detected": len(cons),
                    "contradictions_open": sum(1 for c in cons if c.review_status == "needs_review"),
                    "gaps_unresolved": gp["unresolved"], "gaps_total": gp["total"]},
        "progress": {"overall": round(sum(comps.values()) / len(comps), 3), "components": {k: round(v, 3) for k, v in comps.items()}},
        "categories": [{"key": k, "label": CATEGORY_LABEL[k], "count": v} for k, v in sorted(cats.items())],
        "hourly_activity": [{"hour": h, "records": hourly.get(h, 0)} for h in [f"{x:02d}:00" for x in range(18, 24)]],
        "recent_events": events[:10], "synthetic": True, "label": config.SYNTHETIC_LABEL,
    }


def case_payload(s: Session) -> dict:
    c = s.query(DemoCase).first()
    return {"id": c.id, "title": c.title, "summary": c.summary, "status": c.status, "opened_at": c.opened_at.isoformat(),
            "jurisdiction": c.jurisdiction, "lead_investigator": c.lead_investigator, "master_clock": c.master_clock,
            "synthetic": True, "label": config.SYNTHETIC_LABEL, "watermark": config.WATERMARK}


def entity_profile(s: Session, eid: str) -> dict | None:
    e = s.get(DemoEntity, eid)
    if not e:
        return None
    from .models import DemoRelation
    rels = [r for r in s.query(DemoRelation) if eid in (r.source, r.target)]
    ev = [r for r in s.query(DemoEvidence) if eid in (r.persons or []) or r.source_device == eid]
    matches = [ser_match(m, s) for m in s.query(DemoIdentityMatch) if eid in (m.entity_a, m.entity_b)]
    return {"id": e.id, "type": e.type, "label": e.label, "role": e.role, "attrs": e.attrs,
            "relations": [{"id": r.id, "other": r.target if r.source == eid else r.source, "direction": "out" if r.source == eid else "in",
                           "kind": r.kind, "confidence": r.confidence, "evidence_ids": r.evidence_ids} for r in rels],
            "evidence": [ser_evidence(x) for x in sorted(ev, key=lambda x: x.id)][:60], "evidence_count": len(ev),
            "identity_matches": matches, "synthetic": True}


def audit_log(s: Session, limit=100) -> list[dict]:
    return [{"id": a.id, "ts": a.ts.isoformat(), "action": a.action, "detail": a.detail, "session": a.session}
            for a in s.query(DemoAudit).order_by(DemoAudit.id.desc()).limit(limit)]


def audit(s: Session, action: str, detail: dict | None = None, session: str = "demo-visitor") -> None:
    s.add(DemoAudit(ts=datetime.now(), action=action, detail=detail or {}, session=session))


def digest(s: Session, start=None, end=None) -> str:
    """Compact, ID-tagged text rendering of the case for LLM prompts."""
    lines = []
    for e in s.query(DemoEvidence).order_by(DemoEvidence.id):
        t = analytics.event_time(e)
        if (start and t < start) or (end and t > end):
            continue
        lines.append(f"{e.id} | {e.category} | {t:%Y-%m-%d %H:%M} | {summarize(e)}")
    return "\n".join(lines)

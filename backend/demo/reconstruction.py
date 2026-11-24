"""Five-agent reconstruction workflow: Extractor -> Correlator -> Hypothesis -> Critic -> Report.

Each step records HOW it was produced (``produced_by``). In precomputed mode the
hypothesis/critic text is seeded and replayed; extractor, correlator and the
report skeleton are rule-based computations over the demo database. Only steps
actually produced by a model carry an ``llm:`` label.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

import networkx as nx
from sqlalchemy.orm import Session

from . import analytics, llm, queries
from .models import DemoEvidence, DemoGap, DemoHypothesis, DemoIdentityMatch

RULE = "rule-based computation over database records"
SEEDED = "precomputed (seeded) demo intelligence"


def _extractor(s: Session) -> dict:
    cats = Counter(e.category for e in s.query(DemoEvidence))
    facts = []
    txs = [e for e in s.query(DemoEvidence).filter_by(category="transaction") if e.content["amount_inr"] >= 100000]
    for e in sorted(txs, key=lambda x: x.corrected_ts):
        facts.append({"fact": f"{queries.summarize(e)} at {e.corrected_ts:%H:%M}.", "evidence_ids": [e.id]})
    for d in s.query(DemoEvidence).filter_by(category="device_log"):
        if d.content["log_type"] in ("sim_activation", "bank_notification", "upi_registration"):
            facts.append({"fact": queries.summarize(d), "evidence_ids": [d.id]})
    from .models import DemoEntity
    for dev in s.query(DemoEntity).filter_by(type="device"):
        off = (dev.attrs or {}).get("clock_offset_seconds", 0)
        if off:
            ev = [e.id for e in s.query(DemoEvidence).filter_by(source_device=dev.id) if e.clock_offset_seconds][:6]
            facts.append({"fact": f"{dev.id} clock is {abs(off) // 60} minutes {'behind' if off < 0 else 'ahead of'} the master clock; "
                                  "its timestamps were corrected.", "evidence_ids": ev})
    for e in s.query(DemoEvidence).filter_by(category="statement"):
        facts.append({"fact": queries.summarize(e), "evidence_ids": [e.id]})
    return {"agent": "Extractor", "produced_by": RULE,
            "summary": f"Extracted {len(facts)} key facts from {sum(cats.values())} records ({', '.join(f'{v} {k}' for k, v in sorted(cats.items()))}).",
            "facts": facts}


def _correlator(s: Session) -> dict:
    g = analytics.build_graph(s)
    links = []
    for ent in s.query(analytics.DemoEntity).filter_by(type="event"):
        a = ent.attrs or {}
        links.append({"link": ent.label, "evidence_ids": a.get("evidence_ids") or a.get("validated_by") or []})
    for m in s.query(DemoIdentityMatch):
        links.append({"link": f"Possible same identity: {m.entity_a} ↔ {m.entity_b} (score {m.score:.2f}, {m.status})",
                      "evidence_ids": m.evidence_ids or []})
    try:
        path = nx.shortest_path(g.to_undirected(), "ACC-NEXA", "UPI-RAJU")
        links.append({"link": "Money-flow path: " + " → ".join(path), "evidence_ids":
                      [e.id for e in s.query(DemoEvidence).filter_by(category="transaction")
                       if e.content["to_account"] in ("ACC-D", "UPI-RAJU") and e.content["amount_inr"] >= 100000]})
    except nx.NetworkXNoPath:
        pass
    pairs = [r for r in s.query(analytics.DemoRelation).filter_by(kind="communicates_with")]
    for r in sorted(pairs, key=lambda r: -r.confidence)[:5]:
        links.append({"link": f"{r.source} ↔ {r.target}: {r.note}", "evidence_ids": (r.evidence_ids or [])[:6]})
    return {"agent": "Correlator", "produced_by": RULE,
            "summary": f"Built a graph of {g.number_of_nodes()} entities and {g.number_of_edges()} relationships; surfaced {len(links)} cross-record links.",
            "links": links}


def _auto_checks(s: Session, hyps: list[dict]) -> list[dict]:
    """Rule-based sanity checks the critic always applies."""
    known = {e.id: e for e in s.query(DemoEvidence)}
    out = []
    for h in hyps:
        sup = [x["evidence_id"] for x in h["supporting"]]
        missing = [i for i in sup + [x["evidence_id"] for x in h["contradicting"]] if i not in known]
        loc_only = [i for i in sup if known.get(i) and known[i].category in ("gps", "cdr")]
        out.append({"scenario": h["id"], "nonexistent_ids": missing,
                    "device_location_evidence_ids": loc_only,
                    "flag": ("Claims about a person's presence rest on device/tower location records, which do not establish "
                             "physical presence." if loc_only else None),
                    "has_contradicting_evidence": bool(h["contradicting"])})
    return out


def _from_seed(s: Session) -> list[dict]:
    return [queries.ser_hypothesis(h) for h in s.query(DemoHypothesis).order_by(DemoHypothesis.id)]


def _from_llm(s: Session, mode: str) -> tuple[list[dict] | None, str | None, str | None]:
    known = {e.id for e in s.query(DemoEvidence)}
    prompt = (
        "Evidence records (ID | category | time | summary):\n" + queries.digest(s) +
        "\n\nTask: propose exactly three competing scenarios for the evening of 14 March 2026, challenge each as a critic, "
        "and write a short report summary. Reply with JSON only: {\"scenarios\":[{\"title\",\"description\","
        "\"supporting\":[{\"evidence_id\",\"note\"}],\"contradicting\":[{\"evidence_id\",\"note\"}],\"confidence\":0-1,"
        "\"reasoning\",\"missing\":[...],\"critic\":[{\"claim\",\"challenge\",\"evidence_ids\":[...],\"verdict\"}]}],\"summary\":\"...\"}. "
        "Every evidence_id must appear in the records above.")
    try:
        data = llm.extract_json(llm.chat(mode, llm.GROUNDING_RULES, prompt))
        out = []
        for i, sc in enumerate(data["scenarios"][:3], 1):
            ids = [x["evidence_id"] for x in sc.get("supporting", []) + sc.get("contradicting", [])]
            ids += [e for c in sc.get("critic", []) for e in c.get("evidence_ids", [])]
            _, bad = llm.validate_ids(ids, known)
            if bad:
                return None, None, f"model cited nonexistent evidence IDs: {sorted(set(bad))}"
            out.append({"id": f"LLM-H-{i}", "title": sc["title"], "description": sc["description"],
                        "supporting": sc.get("supporting", []), "contradicting": sc.get("contradicting", []),
                        "confidence": float(sc.get("confidence", 0)), "reasoning": sc.get("reasoning", ""),
                        "missing": sc.get("missing", []), "critic": sc.get("critic", []), "synthetic": True})
        if len(out) != 3:
            return None, None, "model did not return three scenarios"
        return out, data.get("summary", ""), None
    except Exception as exc:  # network, parsing, schema
        return None, None, f"model call failed: {type(exc).__name__}: {exc}"


def report_summary(s: Session, hyps: list[dict]) -> dict:
    ov = queries.overview(s)
    m = ov["metrics"]
    top = max(hyps, key=lambda h: h["confidence"])
    cons = [c for c in s.query(queries.DemoContradiction)]
    gaps = queries.gaps_payload(s)
    text = (f"The vault holds {m['evidence_records']} synthetic records on {m['people']} people and {m['devices']} devices. "
            f"{m['contradictions_detected']} contradictions were flagged ({m['contradictions_open']} awaiting review) and "
            f"{gaps['unresolved']} of {gaps['total']} evidence gaps remain open, including missing lobby CCTV for 21:08–21:31. "
            f"The best-supported scenario is “{top['title']}” at seeded confidence {top['confidence']:.2f}; this is an analyst-style estimate, "
            "not a probability, and presence of people (as opposed to devices) at Sector 18 is not established.")
    ids = sorted({c.statement_evidence_id for c in cons} | {x["evidence_id"] for x in top["supporting"][:4]})
    return {"text": text, "evidence_ids": ids}


def run(s: Session, requested_mode: str | None) -> dict:
    mode = llm.resolve_mode(requested_mode)
    started = datetime.now()
    steps = [_extractor(s), _correlator(s)]
    fallback = None
    hyps, summary, produced = None, None, SEEDED
    if mode != "precomputed":
        hyps, summary, fallback = _from_llm(s, mode)
        if hyps:
            produced = f"llm:{mode}"
    if not hyps:
        hyps = _from_seed(s)
        mode_used = "precomputed"
    else:
        mode_used = mode
    steps.append({"agent": "Hypothesis", "produced_by": produced if mode_used != "precomputed" else SEEDED,
                  "summary": "Three competing scenarios.", "scenarios": hyps})
    steps.append({"agent": "Critic", "produced_by": (produced if mode_used != "precomputed" else SEEDED) + " + rule-based checks",
                  "summary": "Challenged each scenario against available evidence.",
                  "challenges": [{"scenario": h["id"], "items": h["critic"]} for h in hyps],
                  "automatic_checks": _auto_checks(s, hyps)})
    rep = report_summary(s, hyps) if not summary else {"text": summary, "evidence_ids": []}
    steps.append({"agent": "Report", "produced_by": (f"llm:{mode_used}" if summary else RULE),
                  "summary": "Final investigation summary.", "report": rep})
    return {"mode_requested": requested_mode or "precomputed", "mode_used": mode_used,
            "mode_label": llm.MODE_LABELS[mode_used],
            "banner": ("Replay of precomputed demo intelligence – not newly generated by an AI model."
                       if mode_used == "precomputed" else f"Generated by {llm.MODE_LABELS[mode_used]} from the synthetic dataset; cited IDs were validated against the database."),
            "fallback_reason": fallback, "started": started.isoformat(), "steps": steps}

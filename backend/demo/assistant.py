"""AI Investigator Assistant for the demo case.

Precomputed mode answers by deterministic retrieval over the demo database; it
only ever states records it actually found, always with their evidence IDs, and
says so when the dataset has no answer. It is labelled as rule-based retrieval,
never as AI-generated analysis. Local/cloud modes call a model and then
validate every cited evidence ID against the database.
"""
from __future__ import annotations

import re
from datetime import datetime

import networkx as nx
from sqlalchemy.orm import Session

from . import analytics, config, dataset as ds, llm, queries, reconstruction
from .models import (DemoContradiction, DemoEntity, DemoEvidence, DemoGap, DemoHypothesis, DemoIdentityMatch,
                     DemoRelation)

NOT_AVAILABLE = "This is not available in the demo dataset."
PRODUCED_RULE = "precomputed rule-based retrieval over the demo database (not AI-generated)"
CASE_DAY = datetime(2026, 3, 14)


def _people_in(q: str) -> list[str]:
    ql = q.lower()
    found = []
    for m in re.finditer(r"person\s+([a-f])\b", ql):
        found.append(f"P-{m.group(1).upper()}")
    for pid, name, _ in ds.PEOPLE:
        if name.split()[0].lower() in ql or name.lower() in ql:
            found.append(pid)
    if "raju" in ql:
        found.append("P-B")
    # "between A and C" style
    m = re.search(r"between\s+(?:person\s+)?([a-f])\s+and\s+(?:person\s+)?([a-f])\b", ql)
    if m:
        found += [f"P-{m.group(1).upper()}", f"P-{m.group(2).upper()}"]
    out = []
    for p in found:
        if p not in out:
            out.append(p)
    return out


def _parse_hour(h, mnt, mer) -> int:
    h = int(h)
    if mer == "pm" and h < 12:
        h += 12
    if mer == "am" and h == 12:
        h = 0
    return h * 60 + int(mnt or 0)


def _window(q: str):
    m = re.search(r"(?:between|from)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:and|to|-|–)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
                  q.lower())
    if not m:
        return None
    h1, m1, mer1, h2, m2, mer2 = m.groups()
    mer1 = mer1 or mer2
    a, b = _parse_hour(h1, m1, mer1), _parse_hour(h2, m2, mer2)
    if b <= a:
        b += 12 * 60 if b + 720 > a else 0
    base = CASE_DAY
    return base.replace(hour=a // 60 % 24, minute=a % 60), base.replace(hour=min(b // 60, 23), minute=b % 60 if b // 60 < 24 else 59)


def _fmt(e: DemoEvidence) -> str:
    t = analytics.event_time(e)
    tag = " [clock-corrected]" if e.clock_offset_seconds else ""
    return f"{e.id} ({t:%H:%M}{tag}) {queries.summarize(e)}"


def _result(answer, ids, intent, found=True):
    return {"answer": answer, "evidence_ids": list(dict.fromkeys(ids)), "intent": intent, "found": found}


# ---------------------------------------------------------------- intents
def _timewindow(s, q, win):
    a, b = win
    rows = [e for e in s.query(DemoEvidence) if a <= analytics.event_time(e) <= b]
    rows.sort(key=lambda e: (analytics.event_time(e), e.id))
    if not rows:
        return _result(f"No evidence records fall between {a:%H:%M} and {b:%H:%M} on 14 March 2026 in the demo dataset.", [], "time_window", False)
    by = {}
    for e in rows:
        by[e.category] = by.get(e.category, 0) + 1
    lines = [f"Between {a:%H:%M} and {b:%H:%M} on 14 March 2026 the dataset has {len(rows)} records "
             f"({', '.join(f'{v} {k}' for k, v in sorted(by.items()))}). Key events, using clock-corrected times:"]
    shown = rows[:22]
    ids = []
    for e in shown:
        lines.append(f"- {_fmt(e)}")
        ids.append(e.id)
    if len(rows) > len(shown):
        lines.append(f"- …and {len(rows) - len(shown)} more (open the Timeline for the full list).")
    for g in s.query(DemoGap).filter_by(kind="cctv"):
        if g.window_start and g.window_end and g.window_start < b and g.window_end > a:
            lines.append(f"Note: {g.title} overlaps this window ({', '.join(g.evidence_ids)} bound the gap), so lobby activity there is unobserved.")
            ids += g.evidence_ids
    lines.append("Device location records show where a phone was, not necessarily where its owner was.")
    return _result("\n".join(lines), ids, "time_window")


def _owner_name(s, account_id):
    pid, basis = analytics.resolved_owner(s, account_id)
    return pid, basis


def _money_to(s, q, people):
    target = people[0]
    txs = [e for e in s.query(DemoEvidence).filter_by(category="transaction")]
    hits, notes = [], []
    for e in sorted(txs, key=lambda x: x.corrected_ts):
        to_pid, basis = _owner_name(s, e.content["to_account"]) if s.get(DemoEntity, e.content["to_account"]) else (None, "")
        if to_pid == target:
            frm = e.content["from_account"]
            frm_pid, _ = _owner_name(s, frm) if s.get(DemoEntity, frm) else (None, "")
            hits.append((e, frm_pid, basis))
    big = [h for h in hits if h[0].content["amount_inr"] >= 100000]
    if not hits:
        rej = [m for m in s.query(DemoIdentityMatch) if m.entity_b == target and m.status == "rejected"]
        extra = (f" Note: identity match {rej[0].id} linking an account to {queries.person_label(target)} was rejected in this demo session, "
                 "so transfers to that account are no longer attributed to them." if rej else "")
        return _result(f"No transactions in the dataset can be attributed to {queries.person_label(target)} as recipient.{extra}", [], "money_to", False)
    lines = [f"Transfers received by {queries.person_label(target)}:"]
    for e, frm_pid, basis in (big or hits)[:12]:
        who = queries.person_label(frm_pid) if frm_pid else queries.account_label(e.content["from_account"])
        lines.append(f"- {e.id} ({e.corrected_ts:%H:%M}): ₹{ds.inr(e.content['amount_inr'])} from {who} via {e.content['channel']} to "
                     f"{queries.account_label(e.content['to_account'])}. Recipient attribution: {basis}.")
    if any("identity match" in h[2] for h in hits):
        lines.append("The recipient account is attributed through an identity match, not a verified KYC record.")
    lines.append("Beyond what is listed, the dataset has no further inbound transfers for this person.")
    return _result("\n".join(lines), [h[0].id for h in (big or hits)], "money_to")


def _contradictions(s, q):
    cons = s.query(DemoContradiction).order_by(DemoContradiction.id).all()
    lines = [f"{len(cons)} contradictions/discrepancies were detected:"]
    ids = []
    for c in cons:
        lines.append(f"- {c.id} ({c.review_status.replace('_', ' ')}, confidence {c.confidence:.2f}): {c.title}. "
                     f"Statement record {c.statement_evidence_id}; conflicting records {', '.join(c.conflicting_evidence_ids)}.")
        ids += [c.statement_evidence_id] + c.conflicting_evidence_ids
    lines.append("These flag conflicts between records; they do not by themselves establish where anyone physically was.")
    return _result("\n".join(lines), ids, "contradictions")


def _scenario(s, q, n):
    h = s.get(DemoHypothesis, f"H-{n}")
    if not h:
        return _result(f"There is no Scenario {n} in the demo dataset (scenarios 1–3 exist).", [], "scenario", False)
    lines = [f"{h.title} (seeded confidence {h.confidence:.2f}). Supporting evidence:"]
    ids = []
    for x in h.supporting:
        e = s.get(DemoEvidence, x["evidence_id"])
        lines.append(f"- {_fmt(e)} – {x['note']}")
        ids.append(e.id)
    lines.append("Contradicting evidence:")
    for x in h.contradicting:
        e = s.get(DemoEvidence, x["evidence_id"])
        lines.append(f"- {_fmt(e)} – {x['note']}")
        ids.append(e.id)
    return _result("\n".join(lines), ids, "scenario")


def _relationship(s, q, people):
    a, b = people[0], people[1]
    la, lb = queries.person_label(a), queries.person_label(b)
    lines, ids = [f"Relationship between {la} and {lb} based on the dataset:"], []
    rel = [r for r in s.query(DemoRelation).filter_by(kind="communicates_with")
           if {r.source, r.target} == {a, b}]
    if rel:
        r = rel[0]
        lines.append(f"- Communication: {r.note} Examples: {', '.join((r.evidence_ids or [])[:4])}.")
        ids += (r.evidence_ids or [])[:4]
    # direct payments between their accounts
    accs = {pid: [k for k, (_, o) in ds.ACCOUNTS.items() if o == pid] for pid in (a, b)}
    direct = [e for e in s.query(DemoEvidence).filter_by(category="transaction")
              if (e.content["from_account"] in accs[a] and e.content["to_account"] in accs[b])
              or (e.content["from_account"] in accs[b] and e.content["to_account"] in accs[a])]
    if direct:
        tot = sum(e.content["amount_inr"] for e in direct)
        lines.append(f"- Direct payments between their accounts: {len(direct)} transfers totalling ₹{ds.inr(tot)} "
                     f"(e.g. {', '.join(e.id for e in direct[:3])}).")
        ids += [e.id for e in direct[:3]]
    # shared device-location at the same place within 15 minutes
    devs = {pid: [d for d, v in ds.DEVICES.items() if v[2] == pid and v[1] == "phone"] for pid in (a, b)}
    gps = [e for e in s.query(DemoEvidence).filter_by(category="gps")]
    near = []
    for x in gps:
        for y in gps:
            if x.content["device"] in devs[a] and y.content["device"] in devs[b] and x.content["location_id"] == y.content["location_id"] \
                    and abs((x.corrected_ts - y.corrected_ts).total_seconds()) <= 15 * 60:
                near.append((x, y))
    if near:
        x, y = near[0]
        lines.append(f"- Their devices were located at {x.content['place']} within 15 minutes ({x.id} and {y.id}). "
                     "That is device location, not proof the two people met.")
        ids += [x.id, y.id]
    g = analytics.build_graph(s).to_undirected()
    try:
        path = nx.shortest_path(g, a, b)
        lines.append("- Shortest connection in the knowledge graph: " + " → ".join(path) + ".")
    except nx.NetworkXNoPath:
        lines.append("- No connecting path exists in the knowledge graph.")
    if not (rel or direct or near):
        return _result(f"The dataset contains no direct communication, payments or co-location linking {la} and {lb}.", [], "relationship", False)
    return _result("\n".join(lines), ids, "relationship")


def _gaps(s, q):
    gp = queries.gaps_payload(s)
    lines = [f"{gp['unresolved']} of {gp['total']} evidence gaps are unresolved:"]
    ids = []
    for g in gp["items"]:
        if not g["resolved"]:
            lines.append(f"- [{g['kind']}] {g['title']}" + (f" (see {', '.join(g['evidence_ids'][:3])})" if g["evidence_ids"] else ""))
            ids += g["evidence_ids"][:3]
    return _result("\n".join(lines), ids, "gaps")


def _identity(s, q):
    ms = s.query(DemoIdentityMatch).order_by(DemoIdentityMatch.id).all()
    lines = ["Proposed identity connections:"]
    ids = []
    for m in ms:
        lines.append(f"- {m.id}: {m.entity_a} ↔ {m.entity_b}, score {m.score:.2f}, status {m.status}. Evidence: {', '.join(m.evidence_ids[:4]) or 'none cited'}.")
        ids += m.evidence_ids[:4]
    return _result("\n".join(lines), ids, "identity")


def _clock(s, q):
    ev = [e for e in s.query(DemoEvidence) if e.clock_offset_seconds]
    ids = [e.id for e in ev][:8]
    return _result(f"Device DEV-C1 (Chitra's phone) runs 3 minutes behind the master clock. {len(ev)} of its records were corrected by +180 s "
                   f"(e.g. {', '.join(ids[:4])}). The correction is validated by the UPI app log {next(e.id for e in ev if e.category == 'device_log' and e.content['log_type'] == 'upi_app_event')} "
                   "matching the bank record after correction.", ids, "clock")


def _summary(s, q):
    hyps = [queries.ser_hypothesis(h) for h in s.query(DemoHypothesis).order_by(DemoHypothesis.id)]
    r = reconstruction.report_summary(s, hyps)
    lines = [r["text"], "Competing scenarios (seeded confidence): " +
             "; ".join(f"{h['id']} {h['confidence']:.2f}" for h in hyps) + "."]
    return _result("\n".join(lines), r["evidence_ids"], "summary")


def _search(s, q):
    words = [w for w in re.findall(r"[a-z0-9₹@.\-]{3,}", q.lower())
             if w not in {"the", "and", "what", "who", "was", "were", "did", "for", "with", "about", "from", "that", "this", "does", "are", "any", "anyone", "buy", "bought", "have", "has", "there", "their", "they", "them", "show", "tell"}]
    scored = []
    for e in s.query(DemoEvidence):
        text = (queries.summarize(e) + " " + e.title + " " + str(e.content)).lower()
        sc = sum(1 for w in words if w in text) + (3 if e.id.lower() in q.lower() else 0)
        if sc >= min(2, max(len(words), 1)) or e.id.lower() in q.lower():
            scored.append((sc, e))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    if not scored:
        return _result(NOT_AVAILABLE + " I could not match your question to any record, contradiction, scenario or gap.", [], "search", False)
    top = [e for _, e in scored[:6]]
    return _result("I have no dedicated answer for that, but these records match your wording:\n" + "\n".join(f"- {_fmt(e)}" for e in top)
                   + "\nI am not drawing conclusions from them.", [e.id for e in top], "search")


def rule_answer(s: Session, q: str) -> dict:
    ql = q.lower()
    win = _window(q)
    people = _people_in(q)
    m = re.search(r"(?:scenario|hypothesis)\s*#?(\d)", ql)
    if m:
        return _scenario(s, q, int(m.group(1)))
    if win and not re.search(r"relationship", ql):
        return _timewindow(s, q, win)
    if re.search(r"(transferred|transfer|paid|sent|send|money|funds|payment).*(to|received)", ql) and people and "who" in ql:
        return _money_to(s, q, people)
    if "contradict" in ql or "conflict" in ql or "inconsisten" in ql:
        return _contradictions(s, q)
    if re.search(r"relationship|related|connect|link", ql) and len(people) >= 2:
        return _relationship(s, q, people)
    if re.search(r"missing|gap|unknown|not available|what evidence", ql):
        return _gaps(s, q)
    if re.search(r"summar|overview|what happened|brief me", ql):
        return _summary(s, q)
    if re.search(r"alias|identity|same person|second number", ql):
        return _identity(s, q)
    if re.search(r"clock|timestamp|offset|behind", ql):
        return _clock(s, q)
    return _search(s, q)


# ---------------------------------------------------------------- entry point
def ask(s: Session, question: str, requested_mode: str | None = None) -> dict:
    question = (question or "").strip()
    mode = llm.resolve_mode(requested_mode)
    rb = rule_answer(s, question)
    base = {"question": question, "synthetic": True, "label": config.SYNTHETIC_LABEL, "intent": rb["intent"],
            "mode_requested": requested_mode or "precomputed"}
    if mode == "precomputed":
        return {**base, "answer": rb["answer"], "evidence_ids": rb["evidence_ids"], "mode_used": "precomputed",
                "mode_label": llm.MODE_LABELS["precomputed"], "produced_by": PRODUCED_RULE, "grounded": rb["found"],
                "warnings": [] if rb["found"] else [NOT_AVAILABLE]}
    known = {e.id for e in s.query(DemoEvidence)}
    ctx = queries.digest(s, datetime(2026, 3, 14, 20, 0), datetime(2026, 3, 14, 23, 0)) if mode == "local" else queries.digest(s)
    hints = f"\n\nVerified hints computed from the database (you may use them):\n{rb['answer']}" if rb["found"] else ""
    user = f"Evidence records:\n{ctx}{hints}\n\nQuestion: {question}"
    try:
        text = llm.chat(mode, llm.GROUNDING_RULES, user)
    except Exception as exc:
        return {**base, "answer": rb["answer"], "evidence_ids": rb["evidence_ids"], "mode_used": "precomputed",
                "mode_label": llm.MODE_LABELS["precomputed"], "produced_by": PRODUCED_RULE, "grounded": rb["found"],
                "warnings": [f"{mode} model unavailable ({type(exc).__name__}); showing precomputed rule-based answer instead."]}
    ids = llm.cited_ids(text)
    ok, bad = llm.validate_ids(ids, known)
    if bad:
        return {**base, "answer": rb["answer"], "evidence_ids": rb["evidence_ids"], "mode_used": "precomputed",
                "mode_label": llm.MODE_LABELS["precomputed"], "produced_by": PRODUCED_RULE, "grounded": rb["found"],
                "warnings": [f"The {mode} model cited evidence IDs that do not exist ({', '.join(bad)}); its answer was discarded "
                             "and the rule-based answer is shown instead."]}
    warnings = []
    if not ok and NOT_AVAILABLE not in text:
        warnings.append("The model gave no evidence citations; treat this answer as unverified.")
    return {**base, "answer": text, "evidence_ids": ok, "mode_used": mode, "mode_label": llm.MODE_LABELS[mode],
            "produced_by": f"llm:{mode} (citations validated against the database)", "grounded": bool(ok), "warnings": warnings}

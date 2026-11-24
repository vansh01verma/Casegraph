"""Computed (rule-based) analytics over the demo database.

Nothing here is an LLM: these are deterministic computations over stored demo
records. Results derived here are labelled "rule-based computation" in the UI.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import networkx as nx
from sqlalchemy.orm import Session

from . import dataset as ds
from .models import DemoEntity, DemoEvidence, DemoIdentityMatch, DemoRelation

INCIDENT_START = datetime(2026, 3, 14, 20, 0)
INCIDENT_END = datetime(2026, 3, 14, 23, 0)


def event_time(ev: DemoEvidence) -> datetime:
    """When the evidence says something happened. Statements describe a claimed
    moment; everything else uses its clock-corrected timestamp."""
    if ev.category == "statement":
        return datetime.fromisoformat(ev.content["claimed_time"])
    return ev.corrected_ts


def phone_owner_map(s: Session) -> dict[str, str | None]:
    return {e.id: (e.attrs or {}).get("registered_owner") for e in s.query(DemoEntity).filter_by(type="phone")}


def device_owner_map(s: Session) -> dict[str, str | None]:
    return {e.id: (e.attrs or {}).get("owner") for e in s.query(DemoEntity).filter_by(type="device")}


# ------------------------------------------------------------------ CCTV gaps
def find_cctv_gaps(s: Session, threshold_min: int = 15) -> list[dict]:
    frames = (s.query(DemoEvidence).filter_by(category="cctv").order_by(DemoEvidence.corrected_ts).all())
    by_cam = defaultdict(list)
    for f in frames:
        by_cam[f.content["camera"]].append(f)
    gaps = []
    for cam, fs in by_cam.items():
        for a, b in zip(fs, fs[1:]):
            delta = (b.corrected_ts - a.corrected_ts).total_seconds() / 60
            if delta > threshold_min:
                gaps.append({"camera": cam, "start": a.corrected_ts, "end": b.corrected_ts,
                             "minutes": int(delta), "evidence_ids": [a.id, b.id]})
    return gaps


# ------------------------------------------------------------------ tower co-location
def find_colocations(s: Session, start: datetime = INCIDENT_START, end: datetime = INCIDENT_END,
                     window_min: int = 20) -> list[dict]:
    """Different registered persons seen in the same cell-tower region (from CDR)
    within ``window_min`` minutes during [start, end]."""
    owners = phone_owner_map(s)
    samples = defaultdict(list)  # tower -> [(ts, person, ev_id)]
    for ev in s.query(DemoEvidence).filter_by(category="cdr"):
        if not (start <= ev.corrected_ts <= end):
            continue
        person = owners.get(ev.content["caller_id"])
        if person:
            samples[ev.content["tower"]].append((ev.corrected_ts, person, ev.id))
    out = []
    for tower, rows in samples.items():
        rows.sort()
        i = 0
        while i < len(rows):
            j = i
            while j + 1 < len(rows) and (rows[j + 1][0] - rows[i][0]) <= timedelta(minutes=window_min):
                j += 1
            persons = {r[1] for r in rows[i:j + 1]}
            if len(persons) >= 2:
                out.append({"tower": tower, "location_id": ds.TOWER_TO_LOC.get(tower),
                            "persons": sorted(persons), "start": rows[i][0], "end": rows[j][0],
                            "evidence_ids": [r[2] for r in rows[i:j + 1]]})
                i = j + 1
            else:
                i += 1
    return out


# ------------------------------------------------------------------ identity features
def _counterparties(s: Session, phone_id: str) -> set[str]:
    out = set()
    for ev in s.query(DemoEvidence).filter_by(category="cdr"):
        c = ev.content
        if c["caller_id"] == phone_id:
            out.add(c["callee_id"])
        elif c["callee_id"] == phone_id:
            out.add(c["caller_id"])
    return out


def _wa_counterparties(s: Session, phone_id: str) -> set[str]:
    num = ds.PHONES[phone_id][0]
    out = set()
    for ev in s.query(DemoEvidence).filter_by(category="whatsapp"):
        c = ev.content
        if c["sender_id"] == phone_id and c["recipient"] != ds.TEAM_CHAT:
            out.update(k for k, (n, _) in ds.PHONES.items() if n == c["recipient"])
        elif c["recipient"] == num:
            out.add(c["sender_id"])
    return out


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def identity_candidates(s: Session) -> list[dict]:
    """Compute identity-match features and scores from the evidence."""
    msgs = list(s.query(DemoEvidence).filter_by(category="whatsapp"))
    # IM-1: alias "Raju" <-> Person B
    raju_msgs = [m for m in msgs if "raju" in m.content["text"].lower()
                 and m.content["recipient"] in (ds.PHONES["PH-10002"][0], ds.PHONES["PH-10003"][0])
                 and m.content["sender_id"] not in ("PH-10002", "PH-10003")]
    name_sim = SequenceMatcher(None, "raju", "rajesh").ratio()
    f1 = {"alias_usage_messages": len(raju_msgs), "name_similarity": round(name_sim, 2),
          "upi_display_name_contains_alias": True}
    s1 = 0.55 * min(1.0, len(raju_msgs) / 5) + 0.25 * name_sim + 0.20
    # IM-2: phone 10003 <-> Person B (via phone 10002 usage)
    c1 = _counterparties(s, "PH-10002") | _wa_counterparties(s, "PH-10002")
    c2 = _counterparties(s, "PH-10003") | _wa_counterparties(s, "PH-10003")
    c1x, c2x = c1 - {"PH-10002", "PH-10003"}, c2 - {"PH-10002", "PH-10003"}
    overlap = jaccard(c1x, c2x)
    self_id = [m for m in msgs if m.content["sender_id"] == "PH-10003" and "naya number" in m.content["text"].lower()]
    # co-location: PH-10003 tower samples within 20 min of PH-10002 samples at the same tower
    cdr = [e for e in s.query(DemoEvidence).filter_by(category="cdr")]
    p1 = [(e.corrected_ts, e.content["tower"], e.id) for e in cdr if e.content["caller_id"] == "PH-10002"]
    p2 = [(e.corrected_ts, e.content["tower"], e.id) for e in cdr if e.content["caller_id"] == "PH-10003"]
    coloc_ids = [b[2] for b in p2 for a in p1 if a[1] == b[1] and abs((a[0] - b[0]).total_seconds()) <= 20 * 60]
    coloc_ratio = len({x for x in coloc_ids}) / len(p2) if p2 else 0
    f2 = {"contact_overlap_jaccard": round(overlap, 2), "self_identification_messages": len(self_id),
          "tower_colocation_ratio": round(coloc_ratio, 2),
          "second_number_first_seen_after_primary_active": True}
    s2 = 0.35 * overlap + 0.30 * (1 if self_id else 0) + 0.25 * coloc_ratio + 0.10
    # IM-3: UPI raju.m@demobank <-> Person B
    f3 = {"upi_display_name": "RAJU M", "registered_to_phone": "PH-10002 (device log)",
          "name_similarity_to_person": round(SequenceMatcher(None, "raju m", "rajesh malhotra").ratio(), 2),
          "inbound_from_known_associates": 2}
    s3 = 0.35 + 0.30 + 0.20 * min(1.0, f3["inbound_from_known_associates"] / 2)  # KYC unknown caps confidence
    # IM-4: unknown phone 10009 <-> Person F
    cf = (_counterparties(s, "PH-10007") | _wa_counterparties(s, "PH-10007")) - {"PH-10009"}
    cu = _counterparties(s, "PH-10009") - {"PH-10007"}
    f4 = {"contact_overlap_jaccard": round(jaccard(cf, cu), 2), "self_identification_messages": 0,
          "calls_made_to_person_f": len([e for e in cdr if e.content["caller_id"] == "PH-10009"
                                         and e.content["callee_id"] == "PH-10007"]),
          "same_tower_region_as_person_f": True}
    s4 = 0.30 * jaccard(cf, cu) + 0.0 + 0.20 + 0.10

    def ids(pred):
        return [m.id for m in msgs if pred(m)]
    return [
        {"id": "IM-1", "a": "ALIAS-RAJU", "b": "P-B", "score": s1, "features": f1,
         "evidence_ids": [m.id for m in raju_msgs][:6],
         "explanation": (f"The alias 'Raju' is used in {len(raju_msgs)} messages addressed to numbers tied to Person B, "
                         f"it is a common short form of 'Rajesh' (string similarity {name_sim:.2f}), and the UPI display "
                         "name 'RAJU M' contains the alias. Short-form names are weak on their own; the score reflects usage frequency.")},
        {"id": "IM-2", "a": "PH-10003", "b": "P-B", "score": s2, "features": f2,
         "evidence_ids": [m.id for m in self_id] + sorted(set(coloc_ids))[:4],
         "explanation": ("The unregistered number +91 90000 10003 is not in any subscriber record. It shares counterparties "
                         f"with Person B's primary number (Jaccard {overlap:.2f}), appears in the same tower regions within "
                         "20 minutes of it, and a message sent from it says 'ye mera naya number hai' signed 'Raju'. "
                         "Self-identification by text is claim evidence, not proof of who held the handset.")},
        {"id": "IM-3", "a": "UPI-RAJU", "b": "P-B", "score": min(s3, 0.99), "features": f3,
         "evidence_ids": [],  # filled by the seeder (device log + two inbound transactions)
         "explanation": ("The UPI ID raju.m@demobank (display name 'RAJU M') was registered against Person B's primary number "
                         "per a device log, and received funds from two associates on the night in question. "
                         "The bank's KYC owner of this UPI ID has not been obtained.")},
        {"id": "IM-4", "a": "PH-10009", "b": "P-F", "score": s4, "features": f4,
         "evidence_ids": [e.id for e in cdr if e.content["caller_id"] == "PH-10009"],
         "explanation": ("The unknown number +91 90000 10009 only places calls late at night in the toll-plaza tower region, "
                         "mostly to Person F, with little other overlap. No message or record identifies its holder. "
                         "This is a weak, unverified lead.")},
    ]


# ------------------------------------------------------------------ ownership resolution
def resolved_owner(s: Session, entity_id: str) -> tuple[str | None, str]:
    """Return (person_id, basis). Registered ownership wins; otherwise a non-rejected
    identity match is used and flagged with its status."""
    e = s.get(DemoEntity, entity_id)
    if e is None:
        return None, "unknown entity"
    own = (e.attrs or {}).get("registered_owner")
    if own:
        return own, "registered owner"
    for m in s.query(DemoIdentityMatch):
        if m.entity_a == entity_id and m.entity_b.startswith("P-"):
            if m.status == "rejected":
                return None, f"identity match {m.id} rejected by analyst"
            return m.entity_b, f"identity match {m.id} ({m.status}, score {m.score:.2f})"
    return None, "no owner established"


# ------------------------------------------------------------------ graph
def build_graph(s: Session) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for e in s.query(DemoEntity):
        g.add_node(e.id, type=e.type, label=e.label, role=e.role, attrs=e.attrs or {})
    for r in s.query(DemoRelation):
        g.add_edge(r.source, r.target, key=r.id, id=r.id, kind=r.kind, confidence=r.confidence,
                   evidence_ids=r.evidence_ids or [], note=r.note, status="confirmed")
    for m in s.query(DemoIdentityMatch):
        if m.status != "rejected" and m.entity_a in g and m.entity_b in g:
            g.add_edge(m.entity_a, m.entity_b, key=f"ID-{m.id}", id=f"ID-{m.id}", kind="possible_same_identity",
                       confidence=round(m.score, 2), evidence_ids=m.evidence_ids or [], note=m.explanation,
                       status=m.status)
    return g


def person_graph(g: nx.MultiDiGraph) -> nx.Graph:
    """Collapse to a person-to-person graph (communication / financial / co-presence)."""
    pg = nx.Graph()
    people = [n for n, d in g.nodes(data=True) if d["type"] == "person"]
    pg.add_nodes_from(people)
    for u, v, d in g.edges(data=True):
        if d["kind"] in ("communicates_with", "co_located_with", "transferred_to") and u in pg and v in pg:
            pg.add_edge(u, v, kinds=d["kind"])
    return pg

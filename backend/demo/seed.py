"""Seed / reset the demo database. Only ever touches ``demo_*`` tables and the
dedicated demo files directory."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timedelta

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from . import analytics, config, dataset as ds, scenarios as sc
from .db import demo_session, get_engine
from .models import (DemoAudit, DemoBase, DemoCase, DemoContradiction, DemoCustody, DemoEntity, DemoEvidence,
                     DemoGap, DemoHypothesis, DemoIdentityMatch, DemoRelation)

ACTORS = {"cdr": ("Carrier records request (DemoTel, fictional)", "Analyst K. Rao (fictional)"),
          "whatsapp": ("Forensic extraction of source handset", "Examiner S. Dutta (fictional)"),
          "gps": ("Forensic extraction of source handset", "Examiner S. Dutta (fictional)"),
          "transaction": ("Bank records request (DemoBank, fictional)", "Analyst K. Rao (fictional)"),
          "cctv": ("DVR export from building management", "Examiner S. Dutta (fictional)"),
          "statement": ("Statement recorded at station", "Insp. R. Iyer (fictional)"),
          "device_log": ("Forensic extraction of source device", "Examiner S. Dutta (fictional)")}


def canonical_hash(row: dict) -> str:
    payload = json.dumps({"category": row["category"], "source": row["source_device"],
                          "original_ts": row["original_ts"].isoformat(), "content": row["content"]},
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _frame(path, desc: str, ts: datetime, n_people: int) -> bytes:
    img = Image.new("RGB", (640, 360), (14, 22, 38))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 300, 640, 360], fill=(24, 34, 52))
    d.rectangle([470, 70, 590, 300], outline=(60, 120, 160), width=2)  # lift door
    for i in range(n_people):
        x = 150 + i * 90
        d.ellipse([x, 160, x + 30, 190], fill=(90, 110, 130))
        d.rectangle([x - 6, 190, x + 36, 290], fill=(70, 90, 110))
    d.text((12, 10), "SYNTHETIC DEMO FRAME - NOT REAL FOOTAGE", fill=(0, 220, 255))
    d.text((12, 28), f"CAM-S18-LOBBY  {ts:%Y-%m-%d %H:%M:%S}", fill=(200, 210, 225))
    d.text((12, 330), desc[:90], fill=(180, 190, 205))
    img.save(path, "PNG")
    return path.read_bytes()


def _wipe(s: Session) -> None:
    for t in reversed(DemoBase.metadata.sorted_tables):
        s.execute(t.delete())
    if config.DEMO_FILES_DIR.exists():
        shutil.rmtree(config.DEMO_FILES_DIR)
    config.DEMO_FILES_DIR.mkdir(parents=True, exist_ok=True)


def seed(preserve_audit: bool = False) -> dict:
    """(Re)create the demo case from scratch. Returns a small summary."""
    get_engine()
    with demo_session() as s:
        old_audit = []
        if preserve_audit:
            old_audit = [(a.ts, a.action, a.detail, a.session) for a in s.query(DemoAudit)]
        _wipe(s)
        for ts, action, detail, sess in old_audit:
            s.add(DemoAudit(ts=ts, action=action, detail=detail, session=sess))

        s.add(DemoCase(**ds.case_row(), master_clock=config.MASTER_CLOCK, is_synthetic=True))
        _entities(s)
        key_to_id = _evidence(s)
        s.flush()
        _derived(s, key_to_id)
        s.add(DemoAudit(ts=datetime.now(), action="seed", detail={"records": len(key_to_id)}, session="system"))
        return {"evidence": len(key_to_id)}


# ---------------------------------------------------------------- entities
def _entities(s: Session) -> None:
    case = config.DEMO_CASE_ID
    for pid, name, role in ds.PEOPLE:
        s.add(DemoEntity(id=pid, case_id=case, type="person", label=f"{name} (Person {pid[-1]})", role=role,
                         attrs={"name": name, "person_letter": pid[-1]}))
    s.add(DemoEntity(id="ALIAS-RAJU", case_id=case, type="alias", label="Alias: “Raju”",
                     role="Nickname used in messages and UPI display name", attrs={"alias": "Raju"}))
    for did, (label, typ, owner, ph, off) in ds.DEVICES.items():
        s.add(DemoEntity(id=did, case_id=case, type="device", label=label, role=typ,
                         attrs={"device_type": typ, "owner": owner, "phone_id": ph, "clock_offset_seconds": off,
                                "owner_basis": "registered" if owner else "unregistered"}))
    for pid, (num, owner) in ds.PHONES.items():
        s.add(DemoEntity(id=pid, case_id=case, type="phone", label=num,
                         role="registered number" if owner else "unregistered / unknown number",
                         attrs={"number": num, "registered_owner": owner}))
    for lid, (name, lat, lon, tower) in ds.LOCATIONS.items():
        s.add(DemoEntity(id=lid, case_id=case, type="location", label=name, attrs={"lat": lat, "lon": lon, "tower": tower}))
    for aid, (label, owner) in ds.ACCOUNTS.items():
        s.add(DemoEntity(id=aid, case_id=case, type="account", label=label, attrs={"registered_owner": owner, "kind": "bank"}))
    for uid, (vpa, disp) in ds.UPI.items():
        s.add(DemoEntity(id=uid, case_id=case, type="account", label=f"UPI {vpa}",
                         attrs={"registered_owner": None, "kind": "upi", "vpa": vpa, "display_name": disp,
                                "kyc": "not obtained"}))


# ---------------------------------------------------------------- evidence
def _evidence(s: Session) -> dict[str, str]:
    rows = ds.build()
    rows.sort(key=lambda r: (r["corrected_ts"], r["key"]))
    key_to_id: dict[str, str] = {}
    for i, r in enumerate(rows, 1):
        eid = f"EV-{i:04d}"
        key_to_id[r["key"]] = eid
        file_path = None
        if r["category"] == "cctv":
            p = config.DEMO_FILES_DIR / f"{eid}.png"
            data = _frame(p, r["frame"], r["corrected_ts"], r["content"]["persons_visible"])
            file_path = str(p.relative_to(config.DEMO_ROOT))
            sha = hashlib.sha256(data).hexdigest()
            r["content"]["frame_file"] = f"{eid}.png"
        else:
            sha = canonical_hash(r)
        s.add(DemoEvidence(
            id=eid, case_id=config.DEMO_CASE_ID, category=r["category"], title=r["title"], content=r["content"],
            source_device=r["source_device"], original_ts=r["original_ts"], corrected_ts=r["corrected_ts"],
            clock_offset_seconds=r["offset"], sha256=sha, processing_status="processed", file_path=file_path,
            persons=r["persons"], is_synthetic=True))
        acq = datetime(2026, 3, 15, 10, 0) + timedelta(minutes=i * 2)
        how, who = ACTORS[r["category"]]
        for j, (action, delta, note) in enumerate([
                ("acquired", 0, how), ("sha256_computed", 1, "Hash recorded at acquisition"),
                ("ingested_to_vault", 3, "Imported to CaseGraph demo vault (read-only)"),
                ("integrity_verified", 5, "Hash re-verified after ingestion")]):
            s.add(DemoCustody(evidence_id=eid, ts=acq + timedelta(minutes=delta), action=action, actor=who, note=note))
    return key_to_id


# ---------------------------------------------------------------- derived rows
def _derived(s: Session, k: dict[str, str]) -> None:
    case = config.DEMO_CASE_ID
    s.flush()

    def ids(keys):
        missing = [x for x in keys if x not in k]
        if missing:
            raise KeyError(f"unknown evidence key(s) in seed definitions: {missing}")
        return [k[x] for x in keys]

    # ----- analytics -> event entities
    gaps = analytics.find_cctv_gaps(s)
    colocs = analytics.find_colocations(s, datetime(2026, 3, 14, 21, 0), datetime(2026, 3, 14, 21, 30))
    for g in gaps:
        s.add(DemoEntity(id="EVT-CCTVGAP", case_id=case, type="event",
                         label=f"CCTV gap {g['start']:%H:%M}–{g['end']:%H:%M} ({g['minutes']} min)",
                         attrs={"kind": "cctv_gap", **{kk: (v.isoformat() if isinstance(v, datetime) else v) for kk, v in g.items()}}))
    for c in colocs:
        s.add(DemoEntity(id="EVT-COLOC", case_id=case, type="event",
                         label=f"Same tower region {c['tower']} {c['start']:%H:%M}–{c['end']:%H:%M}",
                         attrs={"kind": "tower_colocation", **{kk: (v.isoformat() if isinstance(v, datetime) else v) for kk, v in c.items()}}))
    skew_validation = ids(["upi_log_c", "tx_c_raju"])
    s.add(DemoEntity(id="EVT-CLOCK", case_id=case, type="event", label="Clock skew: DEV-C1 is 3 min behind master",
                     attrs={"kind": "clock_skew", "device": "DEV-C1", "offset_seconds": -180,
                            "validated_by": skew_validation, "observed_delta_seconds": 180}))
    for key, txn in (("tx_nexa_d", "TX-482011"), ("tx_c_raju", "TX-482377"), ("tx_d_raju", "TX-482590")):
        ev = s.get(DemoEvidence, k[key])
        s.add(DemoEntity(id=txn, case_id=case, type="transaction",
                         label=f"₹{ds.inr(ev.content['amount_inr'])} {ev.content['channel']} @ {ev.corrected_ts:%H:%M}",
                         attrs={**ev.content, "evidence_id": ev.id}))
    s.add(DemoEntity(id="TX-DEBIT-9917", case_id=case, type="transaction",
                     label="₹4,50,000 debit to a/c ****9917 @ 22:31 (device alert only)",
                     attrs={"amount_inr": 450000, "evidence_id": k["b2_debit"], "verified": False}))
    s.flush()

    # ----- relations
    n = [0]

    def rel(src, dst, kind, conf, ev_ids, note):
        n[0] += 1
        s.add(DemoRelation(id=f"REL-{n[0]:03d}", case_id=case, source=src, target=dst, kind=kind,
                           confidence=round(conf, 2), evidence_ids=ev_ids[:10], note=note))

    for pid, (num, owner) in ds.PHONES.items():
        if owner:
            rel(owner, pid, "owns_phone", 1.0, [], "Subscriber registration (synthetic).")
    for did, (_, _, owner, ph, _) in ds.DEVICES.items():
        if owner:
            rel(owner, did, "uses_device", 1.0, [], "Registered / habitual user (synthetic).")
        if ph:
            rel(did, ph, "has_phone", 1.0, [], "SIM registered on handset per device logs.")
    for aid, (_, owner) in ds.ACCOUNTS.items():
        if owner:
            rel(owner, aid, "holds_account", 1.0, [], "Account holder per bank records (synthetic).")

    # communication strength between registered persons
    owners = analytics.phone_owner_map(s)
    comm = defaultdict(list)
    for ev in s.query(DemoEvidence).filter(DemoEvidence.category.in_(["cdr", "whatsapp"])):
        c = ev.content
        if ev.category == "cdr":
            a, b = owners.get(c["caller_id"]), owners.get(c["callee_id"])
        else:
            a = owners.get(c["sender_id"])
            b = next((owners.get(pid) for pid, (nm, _) in ds.PHONES.items() if nm == c["recipient"]), None)
            if c["recipient"] == ds.TEAM_CHAT:
                continue
        if a and b and a != b:
            comm[tuple(sorted((a, b)))].append(ev.id)
    for (a, b), evs in comm.items():
        rel(a, b, "communicates_with", min(0.99, 0.6 + 0.02 * len(evs)), evs,
            f"{len(evs)} calls/messages observed between their registered numbers.")
    team = ["P-A", "P-B", "P-C", "P-F"]
    grp = [e.id for e in s.query(DemoEvidence).filter_by(category="whatsapp") if e.content["recipient"] == ds.TEAM_CHAT]
    for i, a in enumerate(team):
        for b in team[i + 1:]:
            if (a, b) not in comm and (b, a) not in comm:
                rel(a, b, "communicates_with", 0.6, grp, "Both are members of the 'Nexa Team' group chat.")

    # money flow
    for txn, key, src, dst in (("TX-482011", "tx_nexa_d", "ACC-NEXA", "ACC-D"), ("TX-482377", "tx_c_raju", "ACC-C", "UPI-RAJU"),
                               ("TX-482590", "tx_d_raju", "ACC-D", "UPI-RAJU")):
        rel(src, txn, "sent", 1.0, [k[key]], "Bank record.")
        rel(txn, dst, "received_by", 1.0, [k[key]], "Bank record.")
    rel("UPI-RAJU", "TX-DEBIT-9917", "sent", 0.7, [k["b2_debit"]], "Based on a device alert only; no bank statement.")
    rel("TX-DEBIT-9917", "ACC-X9917", "received_by", 0.7, [k["b2_debit"]], "Beneficiary unidentified.")
    rel("ALIAS-RAJU", "UPI-RAJU", "display_name_of", 0.8, [], "UPI display name 'RAJU M'.")

    # device -> location (GPS) and phone -> location (tower)
    gps_by = defaultdict(list)
    for ev in s.query(DemoEvidence).filter_by(category="gps"):
        gps_by[(ev.content["device"], ev.content["location_id"])].append(ev.id)
    for (dev, loc), evs in gps_by.items():
        rel(dev, loc, "located_at", 0.9, evs, f"{len(evs)} GPS fix(es). Device location, not proof of the owner's presence.")
    tw_by = defaultdict(list)
    for ev in s.query(DemoEvidence).filter_by(category="cdr"):
        loc = ds.TOWER_TO_LOC.get(ev.content["tower"])
        if loc:
            tw_by[(ev.content["caller_id"], loc)].append(ev.id)
    for (ph, loc), evs in tw_by.items():
        rel(ph, loc, "tower_region", 0.8, evs, f"{len(evs)} call(s) connected via the tower covering this place.")

    # events
    for c in colocs:
        ev_ids = c["evidence_ids"]
        for p in c["persons"]:
            rel(p, "EVT-COLOC", "co_located_with", 0.7, ev_ids, "Same cell-tower region within the stated window (tower region, not exact position).")
        rel("EVT-COLOC", c["location_id"], "occurred_at", 0.8, ev_ids, "Tower coverage area.")
    for g in gaps:
        rel("EVT-CCTVGAP", "LOC-S18", "occurred_at", 1.0, g["evidence_ids"], "No frames between the two evidence records.")
        rel("CAM-S18-LOBBY", "EVT-CCTVGAP", "affected_by", 1.0, g["evidence_ids"], "Missing interval in camera records.")
    rel("DEV-C1", "EVT-CLOCK", "affected_by", 1.0, skew_validation, "Clock offset validated against bank timestamp.")
    rel("CAM-S18-LOBBY", "LOC-S18", "located_at", 1.0, [], "Camera installed in the Orion Business Park lobby.")

    # ----- identity matches
    for m in analytics.identity_candidates(s):
        if m["id"] == "IM-3":
            m["evidence_ids"] = ids(["upi_reg_b1", "tx_c_raju", "tx_d_raju"])
        s.add(DemoIdentityMatch(id=m["id"], case_id=case, entity_a=m["a"], entity_b=m["b"], score=round(m["score"], 2),
                                features=m["features"], explanation=m["explanation"], evidence_ids=m["evidence_ids"],
                                status="proposed", seeded_status="proposed"))

    # ----- contradictions
    for c in sc.CONTRADICTIONS:
        s.add(DemoContradiction(
            id=c["id"], case_id=case, title=c["title"], statement=c["statement"],
            statement_evidence_id=k[c["statement_key"]], conflicting_evidence_ids=ids(c["conflicting"]),
            supporting_evidence_ids=ids(c["supporting"]), time_info=c["time_info"], explanation=c["explanation"],
            caveats=c["caveats"], confidence=c["confidence"], review_status=c["review_status"]))

    # ----- hypotheses
    for h in sc.HYPOTHESES:
        s.add(DemoHypothesis(
            id=h["id"], case_id=case, title=h["title"], description=h["description"],
            supporting=[{"evidence_id": k[key], "note": note} for key, note in h["supporting"]],
            contradicting=[{"evidence_id": k[key], "note": note} for key, note in h["contradicting"]],
            confidence=h["confidence"], reasoning=h["reasoning"], missing=h["missing"],
            critic=[{"claim": c["claim"], "challenge": c["challenge"], "evidence_ids": ids(c["keys"]), "verdict": c["verdict"]}
                    for c in h["critic"]]))

    # ----- gaps
    for i, g in enumerate(gaps, 1):
        s.add(DemoGap(id=f"GAP-CCTV-{i}", case_id=case, kind="cctv",
                      title=f"Missing CCTV: {g['camera']} {g['start']:%H:%M}–{g['end']:%H:%M}",
                      detail=f"No frames for {g['minutes']} minutes, exactly around the Sector 18 hand-off window. Computed from gaps between consecutive frames.",
                      window_start=g["start"], window_end=g["end"], evidence_ids=g["evidence_ids"], severity="high",
                      next_steps=sc.GAP_STEPS["cctv"]))
    s.add(DemoGap(id="GAP-FIN-1", case_id=case, kind="financial",
                  title="Source account and beneficiary for the ₹4,50,000 debit at 22:31 not obtained",
                  detail="Only a device alert documents the transfer to a/c ****9917; no bank statement or KYC is in the vault.",
                  window_start=datetime(2026, 3, 14, 22, 31), window_end=datetime(2026, 3, 14, 22, 31),
                  evidence_ids=[k["b2_debit"]], severity="high", next_steps=sc.GAP_STEPS["financial"]))
    s.add(DemoGap(id="GAP-FIN-2", case_id=case, kind="financial",
                  title="No KYC or statement for UPI ID raju.m@demobank",
                  detail="Two payments (₹4,85,000 and ₹1,35,000) were received, but the UPI ID's account owner is unknown.",
                  evidence_ids=ids(["tx_c_raju", "tx_d_raju"]), severity="medium", next_steps=sc.GAP_STEPS["financial"]))
    unknown_phones = [pid for pid, (_, owner) in ds.PHONES.items() if not owner]
    for pid in unknown_phones:
        ev = [e.id for e in s.query(DemoEvidence).filter_by(category="cdr")
              if pid in (e.content["caller_id"], e.content["callee_id"])]
        s.add(DemoGap(id=f"GAP-PH-{pid[-5:]}", case_id=case, kind="phone",
                      title=f"Unregistered / unknown number {ds.PHONES[pid][0]}",
                      detail=f"No subscriber record. Appears in {len(ev)} call record(s).", evidence_ids=ev[:10],
                      severity="medium", next_steps=sc.GAP_STEPS["phone"]))
    # location gaps: devices of registered people with no GPS in the incident window, and long silences
    window = [e for e in s.query(DemoEvidence).filter_by(category="gps")
              if analytics.INCIDENT_START <= e.corrected_ts <= analytics.INCIDENT_END]
    by_dev = defaultdict(list)
    for e in window:
        by_dev[e.content["device"]].append(e)
    s.add(DemoGap(id="GAP-LOC-1", case_id=case, kind="location",
                  title="No GPS records for Person B's phones during the incident window",
                  detail="Person B (and the candidate second handset) is located only by cell-tower region. Tower regions are wide.",
                  window_start=analytics.INCIDENT_START, window_end=analytics.INCIDENT_END,
                  evidence_ids=ids(["cdr_b1_2114", "cdr_b1_2122"]), severity="medium", next_steps=sc.GAP_STEPS["location"]))
    a = sorted(by_dev.get("DEV-A1", []), key=lambda e: e.corrected_ts)
    for e1, e2 in zip(a, a[1:]):
        mins = int((e2.corrected_ts - e1.corrected_ts).total_seconds() / 60)
        if mins > 30:
            s.add(DemoGap(id="GAP-LOC-2", case_id=case, kind="location",
                          title=f"Person A's phone has no location fix {e1.corrected_ts:%H:%M}–{e2.corrected_ts:%H:%M}",
                          detail=f"{mins}-minute silence between GPS fixes after leaving the Sector 18 office.",
                          window_start=e1.corrected_ts, window_end=e2.corrected_ts, evidence_ids=[e1.id, e2.id],
                          severity="low", next_steps=sc.GAP_STEPS["location"]))
    for m in s.query(DemoIdentityMatch):
        s.add(DemoGap(id=f"GAP-ID-{m.id}", case_id=case, kind="identity",
                      title=f"Unverified identity connection {m.id} (score {m.score:.2f})",
                      detail=m.explanation, evidence_ids=m.evidence_ids, severity="medium" if m.score < 0.8 else "low",
                      next_steps=sc.GAP_STEPS["identity"]))

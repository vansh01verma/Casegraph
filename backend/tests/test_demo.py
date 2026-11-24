import json
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from demo import analytics, config, llm
from demo.db import demo_session
from demo.models import DemoEvidence

G = "/api/demo"
EV = re.compile(r"\bEV-\d{4}\b")


def all_ids(client):
    return {e["id"] for e in client.get(f"{G}/evidence?limit=300").json()["items"]}


# ------------------------------------------------------------------ access / modes
def test_demo_loads_without_authentication_or_api_keys(client):
    r = client.get(f"{G}/overview")  # no auth headers, no keys configured
    assert r.status_code == 200
    m = client.get(f"{G}/mode").json()
    assert m["available"] == {"precomputed": True, "local": False, "cloud": False}
    assert m["active"] == "precomputed"


def test_requesting_unconfigured_ai_mode_falls_back_and_says_so(client):
    r = client.post(f"{G}/assistant", json={"question": "What contradictions were detected?", "mode": "cloud"}).json()
    assert r["mode_used"] == "precomputed"
    assert "not newly generated" in r["mode_label"].lower() or "precomputed" in r["mode_label"].lower()
    assert "AI-generated" in r["produced_by"] and "not AI-generated" in r["produced_by"]


# ------------------------------------------------------------------ dataset
def test_dataset_size_categories_and_synthetic_marking(client):
    d = client.get(f"{G}/evidence?limit=300").json()
    assert 200 <= d["total"] <= 300
    assert {c["key"] for c in d["categories"]} == {"cdr", "whatsapp", "gps", "transaction", "cctv", "statement", "device_log"}
    assert all(i["synthetic"] and i["label"] == "SYNTHETIC DEMO DATA" for i in d["items"])
    assert len({i["sha256"] for i in d["items"]}) == d["total"]          # unique hashes
    assert all(re.fullmatch(r"[0-9a-f]{64}", i["sha256"]) for i in d["items"])
    with demo_session() as s:
        assert all(e.is_synthetic for e in s.query(DemoEvidence))
    people = client.get(f"{G}/entities?type=person").json()["items"]
    assert 5 <= len(people) <= 6


def test_case_and_entities_are_demo_namespaced(client):
    case = client.get(f"{G}/case").json()
    assert case["id"].startswith("DEMO-") and case["synthetic"] and "SYNTHETIC" in case["watermark"]
    ph = [e["label"] for e in client.get(f"{G}/entities?type=phone").json()["items"]]
    assert all(p.startswith("+91 90000 1") for p in ph)                  # reserved fictional block


def test_hash_verification_for_records_and_cctv_frames(client):
    for eid in ("EV-0213", "EV-0205"):
        assert client.get(f"{G}/evidence/{eid}/verify").json()["match"] is True


# ------------------------------------------------------------------ planted clues
def test_clue_clock_skew_corrects_three_minutes(client):
    gps = [e for e in client.get(f"{G}/evidence?category=gps&limit=300").json()["items"]
           if e["source"] == "DEV-C1" and e["corrected_ts"].endswith("21:20:00")][0]
    assert gps["original_ts"].endswith("21:17:00") and gps["clock_offset_seconds"] == -180 and gps["timestamp_corrected"]
    con3 = [c for c in client.get(f"{G}/contradictions").json()["items"] if c["id"] == "CON-3"][0]
    assert con3["review_status"] == "resolved_by_correction"
    log = client.get(f"{G}/evidence/{con3['statement_evidence_id']}").json()
    tx = client.get(f"{G}/evidence/{con3['conflicting_evidence_ids'][0]}").json()
    delta = datetime.fromisoformat(tx["corrected_ts"]) - datetime.fromisoformat(log["original_ts"])
    assert delta.total_seconds() == 180                                  # mismatch is exactly the offset


def test_clue_contradiction_statement_vs_gps_with_caveats(client):
    c = [x for x in client.get(f"{G}/contradictions").json()["items"] if x["id"] == "CON-1"][0]
    stmt = client.get(f"{G}/evidence/{c['statement_evidence_id']}").json()
    assert stmt["category"] == "statement" and "9:20 PM" in stmt["content"]["text"]
    cats = {client.get(f"{G}/evidence/{i}").json()["category"] for i in c["conflicting_evidence_ids"]}
    assert "gps" in cats
    assert c["review_status"] == "needs_review" and 0 < c["confidence"] < 1
    assert "does not by itself prove" in c["explanation"]
    assert any("not proof of the owner's physical presence" in cv for cv in c["caveats"])


def test_clue_witness_vs_gps(client):
    c = [x for x in client.get(f"{G}/contradictions").json()["items"] if x["id"] == "CON-2"][0]
    w = client.get(f"{G}/evidence/{c['statement_evidence_id']}").json()
    assert w["content"]["statement_type"] == "witness"
    assert {client.get(f"{G}/evidence/{i}").json()["category"] for i in c["conflicting_evidence_ids"]} >= {"gps"}


def test_clue_two_identifiers_same_person(client):
    m = {x["id"]: x for x in client.get(f"{G}/identity").json()["items"]}
    assert m["IM-2"]["entity_a"] == "PH-10003" and m["IM-2"]["entity_b"] == "P-B"
    assert m["IM-1"]["entity_a"] == "ALIAS-RAJU"
    assert all(0 < x["score"] < 1 and x["explanation"] and x["status"] == "proposed" for x in m.values())
    assert m["IM-2"]["features"]["contact_overlap_jaccard"] > 0.5        # computed, not hard-coded text


def test_clue_transaction_connects_two_entities(client):
    tx = [e for e in client.get(f"{G}/evidence?category=transaction&limit=300").json()["items"] if "485,000" in e["summary"] or "4,85,000" in e["summary"]]
    assert tx and "ACC-C" in tx[0]["title"] and "UPI-RAJU" in tx[0]["title"]


def test_clue_cctv_gap_is_computed_from_records(client):
    gaps = [g for g in client.get(f"{G}/gaps").json()["items"] if g["kind"] == "cctv"]
    assert len(gaps) == 1 and gaps[0]["window_start"].endswith("21:08:00") and gaps[0]["window_end"].endswith("21:31:00")
    frames = client.get(f"{G}/evidence?category=cctv&limit=300").json()["items"]
    assert not [f for f in frames if "21:08:00" < f["corrected_ts"][11:19] < "21:31:00"]
    for eid in gaps[0]["evidence_ids"]:
        assert client.get(f"{G}/files/{eid}").headers["content-type"] == "image/png"


def test_clue_two_people_same_tower_window(client):
    with demo_session() as s:
        c = analytics.find_colocations(s, datetime(2026, 3, 14, 21, 0), datetime(2026, 3, 14, 21, 30))
    assert len(c) == 1 and c[0]["persons"] == ["P-A", "P-B"] and c[0]["tower"] == "TWR-S18"
    assert (c[0]["end"] - c[0]["start"]).total_seconds() <= 20 * 60


# ------------------------------------------------------------------ modules read the database
def test_overview_metrics_come_from_database(client):
    m = client.get(f"{G}/overview").json()["metrics"]
    assert m["evidence_records"] == client.get(f"{G}/evidence?limit=1").json()["total"]
    assert m["people"] == 6 and m["devices"] == 10 and m["transactions"] == 48
    assert m["contradictions_detected"] == 3 and m["gaps_unresolved"] == 11
    with demo_session() as s:                                           # mutate DB -> API follows
        e = s.get(DemoEvidence, "EV-0001")
        e.title = "DB-DRIVEN-TITLE-XYZ"
    assert client.get(f"{G}/evidence/EV-0001").json()["title"] == "DB-DRIVEN-TITLE-XYZ"


def test_evidence_search_filter_and_details(client):
    assert client.get(f"{G}/evidence?q=naya number").json()["total"] >= 2
    cdr = client.get(f"{G}/evidence?category=cdr&limit=300").json()
    assert cdr["total"] == 61 and all(i["category"] == "cdr" for i in cdr["items"])
    by_person = client.get(f"{G}/evidence?person=P-E&limit=300").json()
    assert by_person["total"] >= 1
    d = client.get(f"{G}/evidence/EV-0213").json()
    assert {"original_ts", "corrected_ts", "sha256", "processing_status", "content", "custody", "cited_in"} <= set(d)
    assert [c["action"] for c in d["custody"]] == ["acquired", "sha256_computed", "ingested_to_vault", "integrity_verified"]
    assert client.get(f"{G}/evidence/EV-9999").status_code == 404


def test_entity_profile(client):
    p = client.get(f"{G}/entities/P-B").json()
    assert p["evidence_count"] > 5 and p["relations"] and any(m["id"] == "IM-2" for m in p["identity_matches"])
    assert client.get(f"{G}/entities/NOPE").status_code == 404


def test_graph_nodes_edges_neighbors_and_filters(client):
    g = client.get(f"{G}/graph").json()
    assert {"person", "device", "phone", "location", "account", "transaction", "event"} <= set(g["types"])
    ids = {n["id"] for n in g["nodes"]}
    known = all_ids(client)
    assert g["edges"] and all(e["source"] in ids and e["target"] in ids and 0 <= e["confidence"] <= 1 for e in g["edges"])
    assert all(set(e["evidence_ids"]) <= known for e in g["edges"])            # edges cite real evidence
    assert any(e["kind"] == "possible_same_identity" and e["status"] == "proposed" for e in g["edges"])
    f = client.get(f"{G}/graph?types=person").json()
    assert {n["type"] for n in f["nodes"]} == {"person"}
    nb = client.get(f"{G}/graph/neighbors/P-C").json()
    assert {"P-C"} <= {n["id"] for n in nb["nodes"]} and nb["edges"] and all("P-C" in (e["source"], e["target"]) for e in nb["edges"])
    assert client.get(f"{G}/graph/neighbors/NOPE").status_code == 404


def test_timeline_filtering(client):
    full = client.get(f"{G}/timeline").json()
    assert full["count"] > 40 and all("2026-03-14T20:00" <= e["ts"] <= "2026-03-14T23:00:01" for e in full["events"])
    only = client.get(f"{G}/timeline?types=transaction").json()
    assert only["count"] >= 3 and {e["category"] for e in only["events"]} == {"transaction"}
    pc = client.get(f"{G}/timeline?persons=P-C").json()
    assert pc["count"] and all("P-C" in e["persons"] for e in pc["events"])
    win = client.get(f"{G}/timeline?start=2026-03-14T21:15:00&end=2026-03-14T21:30:00").json()
    assert win["count"] and all("21:15" <= e["ts"][11:16] <= "21:30" for e in win["events"])
    corrected = [e for e in full["events"] if e.get("timestamp_corrected")]
    assert corrected and all(e["original_ts"] != e["corrected_ts"] for e in corrected)
    wide = client.get(f"{G}/timeline?scope=all").json()
    assert wide["count"] > full["count"]
    cats = {e["category"] for e in wide["events"]}
    assert {"cdr", "whatsapp", "transaction", "gps", "cctv", "statement"} <= cats


def test_contradiction_details_reference_real_evidence(client):
    known = all_ids(client)
    for c in client.get(f"{G}/contradictions").json()["items"]:
        refs = {c["statement_evidence_id"], *c["conflicting_evidence_ids"], *c["supporting_evidence_ids"]}
        assert refs <= known and c["time_info"] and c["explanation"] and c["caveats"]


def test_contradiction_review_status_updates(client):
    r = client.post(f"{G}/contradictions/CON-1/review", json={"status": "confirmed_conflict"}).json()
    assert r["review_status"] == "confirmed_conflict"
    assert client.post(f"{G}/contradictions/CON-1/review", json={"status": "bogus"}).status_code == 422


# ------------------------------------------------------------------ reconstruction
def test_reconstruction_returns_evidence_backed_scenarios(client):
    known = all_ids(client)
    r = client.post(f"{G}/reconstruction/run", json={}).json()
    assert [s["agent"] for s in r["steps"]] == ["Extractor", "Correlator", "Hypothesis", "Critic", "Report"]
    assert r["mode_used"] == "precomputed" and "not newly generated" in r["banner"]
    steps = {s["agent"]: s for s in r["steps"]}
    hyps = steps["Hypothesis"]["scenarios"]
    assert len(hyps) == 3
    for h in hyps:
        assert h["description"] and h["supporting"] and h["contradicting"] and h["reasoning"] and h["missing"]
        assert 0 < h["confidence"] < 1 and h["critic"]
        assert {x["evidence_id"] for x in h["supporting"] + h["contradicting"]} <= known
    assert "precomputed" in steps["Hypothesis"]["produced_by"] and "llm" not in steps["Hypothesis"]["produced_by"]
    chk = {c["scenario"]: c for c in steps["Critic"]["automatic_checks"]}
    assert all(not c["nonexistent_ids"] for c in chk.values()) and chk["H-1"]["flag"]
    for f in steps["Extractor"]["facts"]:
        assert set(f["evidence_ids"]) <= known and f["evidence_ids"]
    assert set(steps["Report"]["report"]["evidence_ids"]) <= known


def test_critic_challenge_endpoint(client):
    r = client.post(f"{G}/hypotheses/H-2/challenge").json()
    assert r["critic"] and any("unsupported" in c["verdict"] for c in r["critic"])
    assert client.post(f"{G}/hypotheses/H-9/challenge").status_code == 404


# ------------------------------------------------------------------ assistant
QUESTIONS = ["What happened between 9 PM and 10 PM?", "Who transferred money to Person B?", "What contradictions were detected?",
             "Which evidence supports Scenario 1?", "What is the relationship between Person A and Person C?",
             "Which evidence is missing?", "Summarize the investigation."]


@pytest.mark.parametrize("q", QUESTIONS)
def test_assistant_answers_use_real_data_and_cite_only_real_ids(client, q):
    known = all_ids(client)
    r = client.post(f"{G}/assistant", json={"question": q}).json()
    assert r["grounded"] and r["evidence_ids"] and set(r["evidence_ids"]) <= known
    assert set(EV.findall(r["answer"])) <= known
    assert r["mode_used"] == "precomputed" and "not AI-generated" in r["produced_by"]


def test_assistant_specific_answers(client):
    a = client.post(f"{G}/assistant", json={"question": "Who transferred money to Person B?"}).json()["answer"]
    assert "Chitra Nair" in a and "4,85,000" in a and "Deepak Sharma" in a and "1,35,000" in a and "IM-3" in a
    a = client.post(f"{G}/assistant", json={"question": "What happened between 9 PM and 10 PM?"}).json()["answer"]
    assert "21:20" in a and "overlaps this window" in a
    a = client.post(f"{G}/assistant", json={"question": "Which evidence is missing?"}).json()["answer"]
    assert "CCTV" in a and "4,50,000" in a and "KYC" in a


def test_assistant_says_when_answer_unavailable_and_never_invents(client):
    r = client.post(f"{G}/assistant", json={"question": "Did anyone buy a yacht in Monaco?"}).json()
    assert not r["grounded"] and "not available in the demo dataset" in r["answer"] and r["evidence_ids"] == []
    r = client.post(f"{G}/assistant", json={"question": "What is the relationship between Person A and Person Z?"}).json()
    assert set(EV.findall(r["answer"])) <= all_ids(client)
    assert client.post(f"{G}/assistant", json={"question": "  "}).status_code == 422


def test_llm_mode_validates_citations_and_labels_output(client):
    config.CLOUD_LLM_API_KEY = "test-key"
    assert client.get(f"{G}/mode").json()["available"]["cloud"] is True
    llm.set_transport(lambda mode, system, user: "Chitra's UPI payment is recorded in EV-0213 at 21:24.")
    r = client.post(f"{G}/assistant", json={"question": "What did Chitra pay?", "mode": "cloud"}).json()
    assert r["mode_used"] == "cloud" and r["produced_by"].startswith("llm:cloud") and r["evidence_ids"] == ["EV-0213"]
    llm.set_transport(lambda mode, system, user: "She paid it, see EV-9999.")          # invented ID
    r = client.post(f"{G}/assistant", json={"question": "What did Chitra pay?", "mode": "cloud"}).json()
    assert r["mode_used"] == "precomputed" and any("EV-9999" in w for w in r["warnings"]) and "EV-9999" not in r["answer"]
    llm.set_transport(lambda mode, system, user: "Probably yes.")                      # no citations
    r = client.post(f"{G}/assistant", json={"question": "What did Chitra pay?", "mode": "cloud"}).json()
    assert r["mode_used"] == "cloud" and r["warnings"] and not r["grounded"]
    def boom(*a):
        raise RuntimeError("network down")
    llm.set_transport(boom)
    r = client.post(f"{G}/assistant", json={"question": "Summarize the investigation.", "mode": "cloud"}).json()
    assert r["mode_used"] == "precomputed" and any("unavailable" in w for w in r["warnings"])


def test_llm_reconstruction_valid_and_invalid_ids(client):
    config.CLOUD_LLM_API_KEY = "test-key"
    def scen(i, eid):
        return {"title": f"S{i}", "description": "d", "supporting": [{"evidence_id": eid, "note": "n"}],
                "contradicting": [{"evidence_id": "EV-0237", "note": "n"}], "confidence": 0.4, "reasoning": "r",
                "missing": ["m"], "critic": [{"claim": "c", "challenge": "x", "evidence_ids": [eid], "verdict": "weakened"}]}
    good = json.dumps({"scenarios": [scen(1, "EV-0213"), scen(2, "EV-0210"), scen(3, "EV-0206")], "summary": "Model summary."})
    llm.set_transport(lambda m, s, u: "```json\n" + good + "\n```")
    r = client.post(f"{G}/reconstruction/run", json={"mode": "cloud"}).json()
    steps = {s["agent"]: s for s in r["steps"]}
    assert r["mode_used"] == "cloud" and steps["Hypothesis"]["produced_by"] == "llm:cloud" and steps["Report"]["report"]["text"] == "Model summary."
    assert steps["Extractor"]["produced_by"].startswith("rule-based")          # honest labelling of non-LLM steps
    bad = good.replace("EV-0206", "EV-8888")
    llm.set_transport(lambda m, s, u: bad)
    r = client.post(f"{G}/reconstruction/run", json={"mode": "cloud"}).json()
    assert r["mode_used"] == "precomputed" and "EV-8888" in r["fallback_reason"]
    assert [x["id"] for x in r["steps"][2]["scenarios"]] == ["H-1", "H-2", "H-3"]


# ------------------------------------------------------------------ identity decisions, reset, audit
def test_identity_accept_reject_has_real_effects(client):
    assert client.post(f"{G}/identity/IM-3/decision", json={"decision": "accept"}).json()["status"] == "accepted"
    before = client.get(f"{G}/gaps").json()["unresolved"]
    assert before == 10                                                         # identity gap closed
    assert client.get(f"{G}/overview").json()["progress"]["components"]["identities_reviewed"] == 0.25
    assert client.post(f"{G}/identity/IM-3/decision", json={"decision": "reject"}).json()["status"] == "rejected"
    a = client.post(f"{G}/assistant", json={"question": "Who transferred money to Person B?"}).json()["answer"]
    assert "No transactions" in a and "rejected" in a                         # attribution follows the analyst's decision
    g = client.get(f"{G}/graph").json()
    assert not [e for e in g["edges"] if e["id"] == "ID-IM-3"]
    assert client.post(f"{G}/identity/IM-3/decision", json={"decision": "maybe"}).status_code == 422
    assert client.post(f"{G}/identity/IM-99/decision", json={"decision": "accept"}).status_code == 404


def test_reset_restores_original_state_and_keeps_audit(client):
    base = (client.get(f"{G}/identity").json(), client.get(f"{G}/contradictions").json(), client.get(f"{G}/overview").json()["metrics"])
    client.post(f"{G}/identity/IM-1/decision", json={"decision": "reject"})
    client.post(f"{G}/contradictions/CON-2/review", json={"status": "dismissed"})
    with demo_session() as s:
        s.get(DemoEvidence, "EV-0001").title = "TAMPERED"
    assert client.get(f"{G}/overview").json()["progress"]["overall"] > 0
    r = client.post(f"{G}/reset").json()
    assert r["status"] == "reset"
    assert (client.get(f"{G}/identity").json(), client.get(f"{G}/contradictions").json(), client.get(f"{G}/overview").json()["metrics"]) == base
    assert client.get(f"{G}/evidence/EV-0001").json()["title"] != "TAMPERED"
    actions = [a["action"] for a in client.get(f"{G}/audit").json()["items"]]
    assert "reset" in actions and "identity_decision" in actions and "contradiction_review" in actions


# ------------------------------------------------------------------ PDF
def test_pdf_report_generates_downloads_and_contains_required_sections(client, tmp_path):
    r = client.post(f"{G}/report/generate").json()
    d = client.get(r["download_url"])
    assert d.status_code == 200 and d.headers["content-type"] == "application/pdf" and d.content[:5] == b"%PDF-"
    import hashlib
    assert hashlib.sha256(d.content).hexdigest() == r["sha256"] and r["pages"] >= 8
    p = tmp_path / "r.pdf"
    p.write_bytes(d.content)
    text = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
    flat = " ".join(text.split())
    for needle in ["SYNTHETIC DEMONSTRATION DATA – NOT A REAL INVESTIGATION", "Investigation summary", "Corrected timeline",
                   "Identity relationships", "Contradictions and discrepancies", "Competing scenarios", "Evidence gaps and recommended next steps",
                   "Evidence inventory and SHA-256 hashes", "Chain of custody", "Missing information", "CON-1", "IM-2", "EV-0213"]:
        assert needle in flat, needle
    ev = client.get(f"{G}/evidence/EV-0213").json()
    assert ev["sha256"] in flat.replace(" ", "")                                # full hash is in the report
    assert "4,85,000" in flat
    assert client.get(f"{G}/report/RPT-nope/download").status_code == 404
    assert client.get(f"{G}/report/..%2f..%2fdemo.db/download").status_code in (404, 422)


# ------------------------------------------------------------------ isolation from live data
def test_demo_never_touches_live_database_or_files(client, tmp_path):
    live = tmp_path / "live.db"
    con = sqlite3.connect(live)
    con.execute("CREATE TABLE cases (id TEXT PRIMARY KEY, title TEXT)")
    con.execute("CREATE TABLE evidence (id TEXT PRIMARY KEY, body TEXT)")
    con.executemany("INSERT INTO cases VALUES (?,?)", [("LIVE-1", "Real case"), ("LIVE-2", "Another")])
    con.execute("INSERT INTO evidence VALUES ('EV-0001', 'LIVE evidence body')")      # same id format as demo on purpose
    con.commit()
    live_files = tmp_path / "uploads"
    live_files.mkdir()
    (live_files / "real.pdf").write_bytes(b"real evidence")
    snap = (con.execute("SELECT * FROM cases").fetchall(), con.execute("SELECT * FROM evidence").fetchall())

    # exercise every mutating endpoint
    client.post(f"{G}/identity/IM-1/decision", json={"decision": "accept"})
    client.post(f"{G}/contradictions/CON-1/review", json={"status": "dismissed"})
    client.post(f"{G}/assistant", json={"question": "Summarize the investigation."})
    client.post(f"{G}/reconstruction/run", json={})
    client.post(f"{G}/report/generate")
    client.post(f"{G}/reset")

    assert (con.execute("SELECT * FROM cases").fetchall(), con.execute("SELECT * FROM evidence").fetchall()) == snap
    assert [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")] == ["cases", "evidence"]
    assert (live_files / "real.pdf").read_bytes() == b"real evidence"
    con.close()
    assert str(live) not in config.DEMO_DATABASE_URL
    assert config.DEMO_ROOT.resolve() not in live.resolve().parents
    # demo files only ever live inside the demo files dir
    assert all(config.DEMO_FILES_DIR.resolve() in p.resolve().parents for p in config.DEMO_FILES_DIR.glob("*"))


def test_demo_module_has_no_live_app_imports_and_demo_tables_are_prefixed():
    pkg = Path(__file__).resolve().parent.parent / "demo"
    stdlib_or_3p = {"__future__", "annotations"}
    for f in pkg.glob("*.py"):
        for line in f.read_text().splitlines():
            m = re.match(r"\s*(?:from|import)\s+([\w.]+)", line)
            if m and m.group(1).startswith(("app", "models", "database", "core", "backend", "main")):
                pytest.fail(f"{f.name} imports live-app module: {line}")
    from demo.models import DemoBase
    assert all(t.startswith("demo_") for t in DemoBase.metadata.tables)


def test_file_endpoint_rejects_unknown_and_traversal(client):
    assert client.get(f"{G}/files/EV-0001").status_code == 404          # not a CCTV record
    assert client.get(f"{G}/files/..%2f..%2fdemo.db").status_code == 404

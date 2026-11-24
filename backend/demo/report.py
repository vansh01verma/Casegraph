"""PDF investigation report for the demo case (ReportLab)."""
from __future__ import annotations

import hashlib
import io
import os
import uuid
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether)
from sqlalchemy.orm import Session
from xml.sax.saxutils import escape

from . import analytics, config, queries, reconstruction
from .models import (DemoCase, DemoContradiction, DemoCustody, DemoEvidence, DemoHypothesis, DemoIdentityMatch)

NAVY, CYAN, SLATE = colors.HexColor("#0b1a2e"), colors.HexColor("#0891b2"), colors.HexColor("#475569")
_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("/Library/Fonts/DejaVuSans.ttf", "/Library/Fonts/DejaVuSans-Bold.ttf", "/Library/Fonts/DejaVuSansMono.ttf"),
    ("C:/Windows/Fonts/DejaVuSans.ttf", "C:/Windows/Fonts/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/DejaVuSansMono.ttf"),
]
_fonts = None


def _register_fonts() -> dict:
    global _fonts
    if _fonts:
        return _fonts
    for reg, bold, mono in _FONT_CANDIDATES:
        if all(os.path.exists(p) for p in (reg, bold, mono)):
            pdfmetrics.registerFont(TTFont("DemoSans", reg))
            pdfmetrics.registerFont(TTFont("DemoSans-Bold", bold))
            pdfmetrics.registerFont(TTFont("DemoMono", mono))
            _fonts = {"sans": "DemoSans", "bold": "DemoSans-Bold", "mono": "DemoMono", "rupee": "\u20b9"}
            return _fonts
    _fonts = {"sans": "Helvetica", "bold": "Helvetica-Bold", "mono": "Courier", "rupee": "Rs. "}
    return _fonts


def _t(text: str, f: dict) -> str:
    return escape(str(text)).replace("\u20b9", f["rupee"])


def _styles(f):
    ss = getSampleStyleSheet()
    base = ParagraphStyle("b", parent=ss["Normal"], fontName=f["sans"], fontSize=9, leading=12.5, textColor=colors.HexColor("#1e293b"))
    return {
        "base": base,
        "small": ParagraphStyle("s", parent=base, fontSize=7.5, leading=10),
        "tiny": ParagraphStyle("t", parent=base, fontName=f["mono"], fontSize=5.3, leading=6.5),
        "h1": ParagraphStyle("h1", parent=base, fontName=f["bold"], fontSize=15, leading=19, textColor=NAVY, spaceBefore=6, spaceAfter=6, keepWithNext=1),
        "h2": ParagraphStyle("h2", parent=base, fontName=f["bold"], fontSize=11, leading=14, textColor=CYAN, spaceBefore=8, spaceAfter=3, keepWithNext=1),
        "title": ParagraphStyle("ti", parent=base, fontName=f["bold"], fontSize=24, leading=29, textColor=NAVY),
        "warn": ParagraphStyle("w", parent=base, fontName=f["bold"], fontSize=9, textColor=colors.HexColor("#b91c1c")),
        "cell": ParagraphStyle("c", parent=base, fontSize=7.2, leading=9),
        "hcell": ParagraphStyle("hc", parent=base, fontName=f["bold"], fontSize=7.2, leading=9, textColor=colors.white),
    }


def _tbl(rows, widths, f, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("FONTNAME", (0, 0), (-1, -1), f["sans"]), ("FONTSIZE", (0, 0), (-1, -1), 7.2),
          ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
               ("FONTNAME", (0, 0), (-1, 0), f["bold"])]
    t.setStyle(TableStyle(st))
    return t


def _page(canvas, doc, f):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 14 * mm, w, 14 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont(f["bold"], 9)
    canvas.drawString(15 * mm, h - 9 * mm, "CaseGraph  \u2022  Demo Investigation Report")
    canvas.setFillColor(colors.HexColor("#67e8f9"))
    canvas.drawRightString(w - 15 * mm, h - 9 * mm, "DEMO MODE \u2022 SYNTHETIC")
    # diagonal watermark
    canvas.setFillColor(colors.Color(0.8, 0.1, 0.1, alpha=0.09))
    canvas.setFont(f["bold"], 30)
    canvas.translate(w / 2, h / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 20, "SYNTHETIC DEMONSTRATION DATA")
    canvas.setFont(f["bold"], 22)
    canvas.drawCentredString(0, -18, "NOT A REAL INVESTIGATION")
    canvas.restoreState()
    canvas.saveState()
    canvas.setFont(f["sans"], 6.8)
    canvas.setFillColor(SLATE)
    canvas.drawString(15 * mm, 8 * mm, config.WATERMARK)
    canvas.drawRightString(w - 15 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report(s: Session) -> tuple[bytes, dict]:
    f = _register_fonts()
    st = _styles(f)
    case = s.query(DemoCase).first()
    ev = s.query(DemoEvidence).order_by(DemoEvidence.id).all()
    hyps = [queries.ser_hypothesis(h) for h in s.query(DemoHypothesis).order_by(DemoHypothesis.id)]
    cons = s.query(DemoContradiction).order_by(DemoContradiction.id).all()
    matches = s.query(DemoIdentityMatch).order_by(DemoIdentityMatch.id).all()
    gaps = queries.gaps_payload(s)
    ov = queries.overview(s)
    P = lambda text, style="base": Paragraph(_t(text, f), st[style])
    el = []
    generated = datetime.now()

    # ---- cover / case details
    el += [Spacer(1, 18 * mm), P("Investigation Report", "title"), P(case.title, "h2"), Spacer(1, 4 * mm),
           P(config.WATERMARK, "warn"), Spacer(1, 6 * mm)]
    el.append(_tbl([[P("Case ID", "cell"), P(case.id, "cell")], [P("Status", "cell"), P(case.status, "cell")],
                    [P("Opened", "cell"), P(f"{case.opened_at:%d %b %Y}", "cell")],
                    [P("Jurisdiction", "cell"), P(case.jurisdiction + " (fictional)", "cell")],
                    [P("Lead investigator", "cell"), P(case.lead_investigator, "cell")],
                    [P("Master clock", "cell"), P(case.master_clock, "cell")],
                    [P("Generated", "cell"), P(f"{generated:%d %b %Y %H:%M} (demo)", "cell")],
                    [P("Data classification", "cell"), P("SYNTHETIC DEMO DATA \u2013 every record, name, number and account is fictional", "cell")]],
                   [40 * mm, 140 * mm], f, header=False))
    # ---- summary
    top = max(hyps, key=lambda h: h["confidence"])
    summary = reconstruction.report_summary(s, hyps)
    el += [P("1. Investigation summary", "h1"), P(case.summary),
           Spacer(1, 2 * mm), P(summary["text"]), Spacer(1, 2 * mm),
           P(f"Source evidence for the summary: {', '.join(summary['evidence_ids'])}.", "small"),
           P("Method note: this summary was assembled by rule-based computation over the demo database and seeded demo intelligence; "
             "it was not newly generated by an AI model.", "small")]
    m = ov["metrics"]
    el.append(_tbl([[P(h, "hcell") for h in ("Evidence records", "People", "Devices", "Transactions", "Contradictions", "Open gaps")],
                    [P(str(x), "cell") for x in (m["evidence_records"], m["people"], m["devices"], m["transactions"],
                                                 m["contradictions_detected"], m["gaps_unresolved"])]],
                   [30 * mm] * 6, f))

    # ---- corrected timeline
    el += [PageBreak(), P("2. Corrected timeline (14 March 2026, 20:00\u201323:00)", "h1"),
           P("Times are corrected to the master clock. Device clock offsets are shown where applied. Statements are placed at the time they claim.", "small"), Spacer(1, 2 * mm)]
    tl = queries.timeline(s, scope="incident")["events"]
    rows = [[P(h, "hcell") for h in ("Time", "Evidence", "Type", "Event", "Recorded / offset")]]
    for e in tl:
        off = (f"{e['original_ts'][11:19]} ({e.get('clock_offset_seconds', 0):+d} s)" if e.get("timestamp_corrected") else "\u2014")
        rows.append([P(e["ts"][11:16], "cell"), P(e["id"], "cell"), P(e["category_label"], "cell"), P(e["summary"][:210], "cell"), P(off, "cell")])
    el.append(_tbl(rows, [13 * mm, 17 * mm, 28 * mm, 98 * mm, 24 * mm], f))

    # ---- identity
    el += [P("3. Identity relationships", "h1")]
    rows = [[P(h, "hcell") for h in ("Match", "Connection", "Score", "Status", "Evidence", "Explanation")]]
    for mm_ in matches:
        d = queries.ser_match(mm_, s)
        rows.append([P(d["id"], "cell"), P(f"{d['entity_a_label']} \u2194 {d['entity_b_label']}", "cell"), P(f"{d['score']:.2f}", "cell"),
                     P(d["status"], "cell"), P(", ".join(d["evidence_ids"][:5]) or "\u2014", "cell"), P(d["explanation"], "cell")])
    el.append(_tbl(rows, [11 * mm, 34 * mm, 11 * mm, 15 * mm, 26 * mm, 83 * mm], f))
    el.append(P("Scores are computed from observable features (alias usage, contact overlap, co-location, self-identification). "
                "Status reflects the analyst's accept/reject decision in the demo session; 'proposed' means unverified.", "small"))

    # ---- contradictions
    el += [PageBreak(), P("4. Contradictions and discrepancies", "h1")]
    for c in cons:
        blk = [P(f"{c.id}: {c.title}", "h2"), P(f"Statement ({c.statement_evidence_id}): {c.statement}"),
               P(f"Conflicting records: {', '.join(c.conflicting_evidence_ids)}. Supporting records: {', '.join(c.supporting_evidence_ids) or 'none'}.", "small"),
               P(f"Explanation: {c.explanation}"), P("Caveats: " + " ".join(c.caveats), "small"),
               P(f"Seeded confidence {c.confidence:.2f}. Review status: {c.review_status.replace('_', ' ')}.", "small")]
        el.append(KeepTogether(blk))

    # ---- scenarios
    el += [PageBreak(), P("5. Competing scenarios", "h1"),
           P("Confidence values are analyst-style seeded estimates for the demo, not calibrated probabilities.", "small")]
    for h in hyps:
        blk = [P(f"{h['title']} \u2013 confidence {h['confidence']:.2f}", "h2"), P(h["description"]), P("Reasoning: " + h["reasoning"], "small")]
        rows = [[P("Supporting", "hcell"), P("Contradicting", "hcell")],
                [Paragraph(_t_markup(h["supporting"], f), st["cell"]), Paragraph(_t_markup(h["contradicting"], f), st["cell"])]]
        blk.append(_tbl(rows, [90 * mm, 90 * mm], f))
        blk.append(P("Missing information: " + "; ".join(h["missing"]), "small"))
        blk.append(P("Critic challenges: " + " | ".join(f"{c['claim']} \u2192 {c['verdict']} ({', '.join(c['evidence_ids'])})" for c in h["critic"]), "small"))
        el.append(KeepTogether(blk))

    # ---- gaps
    el += [P("6. Evidence gaps and recommended next steps", "h1")]
    rows = [[P(h, "hcell") for h in ("Gap", "Type", "Severity", "Status", "Recommended next steps")]]
    for g in gaps["items"]:
        rows.append([P(g["title"], "cell"), P(g["kind"], "cell"), P(g["severity"], "cell"),
                     P("resolved" if g["resolved"] else "open", "cell"), P(" \u2022 ".join(g["next_steps"]), "cell")])
    el.append(_tbl(rows, [50 * mm, 14 * mm, 14 * mm, 12 * mm, 90 * mm], f))

    # ---- evidence inventory (with hashes)
    el += [PageBreak(), P("7. Evidence inventory and SHA-256 hashes", "h1"),
           P(f"{len(ev)} synthetic records. Hashes are SHA-256 of the canonical record content (CCTV frames: of the frame file).", "small"), Spacer(1, 2 * mm)]
    rows = [[P(h, "hcell") for h in ("ID", "Type", "Corrected time", "SHA-256")]]
    for e in ev:
        rows.append([P(e.id, "cell"), P(e.category, "cell"), P(f"{e.corrected_ts:%d %b %H:%M:%S}", "cell"), Paragraph(e.sha256, st["tiny"])])
    el.append(_tbl(rows, [17 * mm, 21 * mm, 28 * mm, 114 * mm], f))

    # ---- chain of custody
    el += [PageBreak(), P("8. Chain of custody", "h1"),
           P("Each record passed four logged steps. Times are acquisition-log times (demo).", "small"), Spacer(1, 2 * mm)]
    cust = {}
    for c in s.query(DemoCustody).order_by(DemoCustody.ts):
        cust.setdefault(c.evidence_id, []).append(c)
    rows = [[P(h, "hcell") for h in ("ID", "Acquired", "Hash computed", "Ingested", "Verified", "Handler")]]
    for e in ev:
        c = {x.action: x for x in cust.get(e.id, [])}
        rows.append([P(e.id, "cell")] + [P(f"{c[a].ts:%d %b %H:%M}", "cell") if a in c else P("\u2014", "cell")
                                         for a in ("acquired", "sha256_computed", "ingested_to_vault", "integrity_verified")]
                    + [P(c["acquired"].actor if "acquired" in c else "\u2014", "cell")])
    el.append(_tbl(rows, [17 * mm, 28 * mm, 28 * mm, 28 * mm, 28 * mm, 51 * mm], f))
    el += [Spacer(1, 4 * mm), P(config.WATERMARK, "warn")]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=20 * mm, bottomMargin=15 * mm,
                            title=f"CaseGraph Demo Report {case.id}", author="CaseGraph Demo Mode",
                            subject=config.WATERMARK)
    doc.build(el, onFirstPage=lambda c, d: _page(c, d, f), onLaterPages=lambda c, d: _page(c, d, f))
    data = buf.getvalue()
    meta = {"report_id": f"RPT-{uuid.uuid4().hex[:10]}", "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "pages": data.count(b"/Type /Page") - data.count(b"/Type /Pages"), "generated_at": generated.isoformat(),
            "watermark": config.WATERMARK}
    return data, meta


def _t_markup(items, f) -> str:
    return "<br/>".join(f"<b>{x['evidence_id']}</b> {escape(x['note']).replace(chr(0x20b9), f['rupee'])}" for x in items) or "\u2014"


def save_report(data: bytes, meta: dict):
    config.ensure_dirs()
    path = config.DEMO_REPORTS_DIR / f"{meta['report_id']}.pdf"
    path.write_bytes(data)
    return path

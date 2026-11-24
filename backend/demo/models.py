"""SQLAlchemy models for Demo Mode. All tables are prefixed ``demo_`` and carry
``is_synthetic`` so no demo row can be confused with live data."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

DemoBase = declarative_base()


class DemoCase(DemoBase):
    __tablename__ = "demo_cases"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text)
    status = Column(String)
    opened_at = Column(DateTime)
    jurisdiction = Column(String)
    lead_investigator = Column(String)
    master_clock = Column(String)
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoEntity(DemoBase):
    """People, devices, phone numbers, locations, accounts, aliases, UPI IDs."""
    __tablename__ = "demo_entities"
    id = Column(String, primary_key=True)          # e.g. P-B, PH-10002, DEV-C1
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    type = Column(String, nullable=False)          # person|device|phone|location|account|upi|alias|tower
    label = Column(String, nullable=False)
    role = Column(String)
    attrs = Column(JSON, default=dict)
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoEvidence(DemoBase):
    __tablename__ = "demo_evidence"
    id = Column(String, primary_key=True)          # EV-0001
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    category = Column(String, nullable=False)      # cdr|whatsapp|gps|transaction|cctv|statement|device_log
    title = Column(String, nullable=False)
    content = Column(JSON, nullable=False)
    source_device = Column(String)                 # entity id of source device/system
    original_ts = Column(DateTime, nullable=False)   # as recorded by the source
    corrected_ts = Column(DateTime, nullable=False)  # after clock-offset correction
    clock_offset_seconds = Column(Integer, default=0)
    sha256 = Column(String(64), nullable=False)
    processing_status = Column(String, default="processed")
    file_path = Column(String)                     # synthetic frame (demo files dir only)
    persons = Column(JSON, default=list)           # entity ids of people involved
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoCustody(DemoBase):
    __tablename__ = "demo_custody"
    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(String, ForeignKey("demo_evidence.id"), nullable=False)
    ts = Column(DateTime, nullable=False)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    note = Column(String)


class DemoRelation(DemoBase):
    __tablename__ = "demo_relations"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence_ids = Column(JSON, default=list)
    note = Column(Text)
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoIdentityMatch(DemoBase):
    __tablename__ = "demo_identity_matches"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    entity_a = Column(String, nullable=False)
    entity_b = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    features = Column(JSON, default=dict)
    explanation = Column(Text)
    evidence_ids = Column(JSON, default=list)
    status = Column(String, default="proposed")    # proposed|accepted|rejected
    seeded_status = Column(String, default="proposed")
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoContradiction(DemoBase):
    __tablename__ = "demo_contradictions"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    title = Column(String, nullable=False)
    statement = Column(Text, nullable=False)
    statement_evidence_id = Column(String)
    conflicting_evidence_ids = Column(JSON, default=list)
    supporting_evidence_ids = Column(JSON, default=list)
    time_info = Column(JSON, default=dict)
    explanation = Column(Text)
    caveats = Column(JSON, default=list)
    confidence = Column(Float)
    review_status = Column(String, default="needs_review")
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoHypothesis(DemoBase):
    __tablename__ = "demo_hypotheses"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    supporting = Column(JSON, default=list)        # [{evidence_id, note}]
    contradicting = Column(JSON, default=list)
    confidence = Column(Float)
    reasoning = Column(Text)
    missing = Column(JSON, default=list)
    critic = Column(JSON, default=list)            # [{claim, challenge, evidence_ids, verdict}]
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoGap(DemoBase):
    __tablename__ = "demo_gaps"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("demo_cases.id"), nullable=False)
    kind = Column(String, nullable=False)          # cctv|financial|phone|location|identity
    title = Column(String, nullable=False)
    detail = Column(Text)
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    evidence_ids = Column(JSON, default=list)
    severity = Column(String, default="medium")
    next_steps = Column(JSON, default=list)
    resolved = Column(Boolean, default=False)
    is_synthetic = Column(Boolean, default=True, nullable=False)


class DemoAudit(DemoBase):
    __tablename__ = "demo_audit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(JSON, default=dict)
    session = Column(String)

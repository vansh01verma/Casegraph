# CaseGraph
### Digital Evidence Correlation & Crime Reconstruction Engine

**An AI-powered digital forensics and investigation support platform.**

CaseGraph is designed to help investigators organize, analyze, correlate, and visualize digital evidence from multiple sources in a unified workspace. It combines evidence management, entity relationship analysis, timeline reconstruction, contradiction detection, and AI-assisted investigation into one platform.

> **Important:** CaseGraph is an investigation support system. AI-generated findings are analytical suggestions, not proof of guilt or substitutes for professional forensic examination.

---

## 1. Project Overview

Modern investigations can involve large volumes of digital evidence, including:

- Call Detail Records (CDR)
- CCTV footage and images
- GPS and location records
- Bank transactions and UPI records
- WhatsApp and other chat records
- Audio recordings
- Device and network logs
- Witness statements
- Digital documents

Analyzing these sources separately can make it difficult to identify relationships, establish event sequences, and detect inconsistencies.

CaseGraph aims to solve this problem by bringing evidence into one structured system and correlating it through entities, events, timestamps, and relationships.

### Key Objectives

- Centralize digital evidence from multiple sources.
- Extract useful information from different evidence formats.
- Identify relationships between people, devices, accounts, and locations.
- Reconstruct event timelines.
- Highlight contradictions and missing evidence.
- Generate multiple possible investigation scenarios.
- Provide traceable, evidence-backed analytical reports.

---

## 2. Core Features

| Feature | Description |
|---|---|
| Case Management | Create and manage investigation cases. |
| Evidence Vault | Organize evidence with metadata, timestamps, and integrity hashes. |
| AI Evidence Extraction | Extract information from supported documents, images, audio, and other formats. |
| Entity Resolution | Identify potentially related people, devices, accounts, and identifiers. |
| Knowledge Graph | Visualize relationships between evidence and entities. |
| Timeline Reconstruction | Arrange events chronologically and compare timestamps. |
| Contradiction Detection | Highlight conflicting statements and records. |
| AI Reconstruction | Generate competing investigation hypotheses. |
| Evidence Gap Analysis | Identify missing information and potential next steps. |
| Investigator Assistant | Ask questions about case evidence with supporting references. |
| Report Generation | Prepare structured investigation reports. |

---

## 3. System Architecture

CaseGraph follows a modular web application architecture.

### Technology Stack

**Frontend**
- React.js
- Vite
- Tailwind CSS
- React Flow / Cytoscape.js
- Recharts
- Leaflet

**Backend**
- Python
- FastAPI
- SQLAlchemy
- Pydantic

**Database and Processing**
- PostgreSQL
- NetworkX
- SHA-256 hashing

**AI and Intelligence**
- Configurable cloud LLM API
- Ollama local-model fallback
- OpenAI Whisper for speech transcription
- Tesseract OCR for text extraction
- YOLO for supported visual object detection
- Sentence Transformers for semantic embeddings

> Actual integrations depend on the configured services and installed models. Optional AI services are not required for the precomputed demonstration workflow.

### High-Level Architecture

```text
             INVESTIGATOR
                  |
                  v
          CASEGRAPH FRONTEND
             React + Vite
                  |
                  v
           FASTAPI BACKEND
                  |
       +----------+----------+
       |          |          |
       v          v          v
   Evidence    Analysis    AI Engine
   Processing  Engine      |
       |          |        +------ Cloud LLM
       |          |        +------ Ollama
       |          |
       v          v
          POSTGRESQL
              |
              v
        KNOWLEDGE GRAPH
              |
              v
       TIMELINE & REPORTS
```

---

## 4. Evidence Processing Workflow

1. **Evidence Collection:** Investigator uploads supported evidence files.
2. **Integrity Verification:** Generate a SHA-256 hash and record evidence metadata.
3. **Information Extraction:** Extract text, entities, events, and timestamps using available processing tools.
4. **Entity Correlation:** Identify possible connections between records.
5. **Timeline Construction:** Arrange extracted events chronologically.
6. **Contradiction Analysis:** Highlight conflicting information and suspicious patterns.
7. **Scenario Reconstruction:** Generate possible explanations supported by available evidence.
8. **Report Generation:** Produce a structured report for investigator review.

Every important analytical claim should be traceable to its supporting evidence.

---

# 5. Demo Mode

## Explore CaseGraph Without Setting Up a Real Investigation

CaseGraph Demo Mode is intended to provide an interactive demonstration of the platform using a fictional financial fraud investigation.

It allows evaluators, students, and developers to explore the system without uploading real investigation data.

### Demo Case

**Case Name:** Project Shadow Transaction  
**Case Type:** Synthetic Financial Fraud Investigation  
**Data Classification:** SYNTHETIC DEMO DATA

The demonstration uses fictional people, accounts, devices, locations, transactions, and events.

### Demo Features

- Preloaded synthetic investigation.
- Evidence Vault with sample records.
- Entity identification and identity resolution.
- Interactive relationship graph.
- Chronological event timeline.
- Location-based event visualization.
- Contradiction detection.
- AI-assisted investigation scenarios.
- Evidence gap analysis.
- Demo investigator assistant.
- Demonstration report generation.

### Synthetic Investigation Clues

The demonstration is designed around the following investigation scenarios:

1. **Witness and GPS Contradiction:** A witness statement conflicts with a recorded device location.
2. **Identity Correlation:** Two different identifiers may belong to the same individual.
3. **Timestamp Difference:** A device clock is three minutes behind the reference clock.
4. **Suspicious Transaction:** A financial transaction connects multiple entities.
5. **Missing CCTV Interval:** A time interval has no available CCTV footage.
6. **Shared Cell Tower Region:** Two devices appear in the same cell tower region during a relevant time window.

These clues demonstrate how CaseGraph can connect information from multiple evidence sources. They do not establish criminal responsibility.

### Demo AI Execution Modes

| Mode | Description |
|---|---|
| Precomputed Demo Intelligence | Uses prepared analytical results for reliable demonstrations without an API key. |
| Local AI | Uses Ollama when a compatible local model is configured. |
| Cloud AI | Uses a configured external LLM API. |

The application should clearly distinguish pre

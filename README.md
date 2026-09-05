# MedLens

## Clinical Intelligence Workspace

MedLens is a privacy-minded clinical workflow prototype for turning clinical reports into structured, reviewable records. It combines deterministic extraction, source-grounded retrieval, provenance tracking, clinician verification, and an optional Gemini-backed language model in one workflow.

MedLens organizes evidence; it does not diagnose, prescribe, triage, or make treatment decisions.

> **Prototype safety notice**
>
> This project is not certified for HIPAA, GDPR, HITECH, FDA SaMD, or any other regulatory use. Do not enter real protected health information (PHI) or personally identifiable information (PII). Use synthetic, de-identified, or openly licensed benchmark data only. See [SECURITY.md](SECURITY.md) for the threat model and production gaps.

## Contents

- [What it does](#what-it-does)
- [Workflow](#workflow)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Configuration](#configuration)
- [Using the application](#using-the-application)
- [API reference](#api-reference)
- [Data and provenance model](#data-and-provenance-model)
- [Safety and security](#safety-and-security)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Development guide](#development-guide)
- [Limitations and roadmap](#limitations-and-roadmap)

## What it does

- Patient intake for symptoms, conditions, allergies, medications, and notes.
- Ingestion of TXT, PDF, DOCX, JSON, HTML, and XML reports.
- Deterministic laboratory extraction with values, units, flags, and source ranges.
- Local TF-IDF chunk indexing and retrieval.
- Grounded question answering with report excerpt citations.
- Side-by-side source review and clinician verification.
- Editing, removal, and addition of observations with provenance history.
- Visible processing and evidence pipeline stages.
- Offline fallback when no LLM key is configured.
- Explicit CORS, upload validation, session scoping, rate limiting, and PHI-redacted logging controls.

## Workflow

1. **Overview**: See workspace health, patients, reports, and entry points.
2. **Patient**: Create or update the patient context.
3. **Reports**: Upload a report file or paste report text.
4. **Structured Record**: Inspect extracted observations and source ranges.
5. **Review**: Compare observations with source text and verify or correct them.
6. **Timeline**: Review documents and recorded history over time.

The **Processing & Evidence** view exposes ingestion, extraction, retrieval, validation, and provenance details for the selected report.

## Architecture

```text
Browser (React + Vite)
        |
        | JSON, multipart uploads, X-Session-ID
        v
FastAPI application (/api)
        |
        +-- Patient and report repositories
        +-- Ingestion, OCR/parsing, and lab extraction services
        +-- Local TF-IDF index and chunk retrieval
        +-- Reference-range and clinical-safety rules
        +-- Optional Gemini client
        +-- Provenance and multi-agent pipeline view
        |
        +-- Local SQLite/filesystem data store
        +-- Optional external LLM provider
```

The backend is the source of truth in live mode. The browser contains a synthetic `DEMO_DATA` dataset so the frontend can be previewed without an API or LLM key.

### Processing principles

- Report content is untrusted clinical evidence, never executable instructions.
- Reference ranges are used only when present in the source or supplied by a clinician.
- Missing ranges produce `not_assessed`; the system does not invent normal ranges.
- AI confidence describes extraction confidence, not medical confidence.
- Answers are grounded in retrieved source content and carry a non-diagnostic boundary.
- Manual review actions preserve context and identify the action as user-verified or user-edited.

## Repository layout

```text
.
├── main.py                         # Uvicorn entry point
├── requirements.txt                # Python dependencies
├── backend/
│   ├── app.py                       # FastAPI assembly, CORS, handlers, routers
│   ├── config.py                    # Environment settings and storage paths
│   ├── api/routes/                  # Health, patients, documents, ingestion, search, pipeline
│   ├── agents/                      # Workflow agent implementations
│   ├── llm/                         # Client, prompts, safety, response schemas
│   ├── models/                      # Domain models
│   ├── repositories/                # Patient and report persistence/search
│   └── services/                    # Extraction, ingestion, summaries, provenance, ranges
├── services/                        # OCR and parser utilities
├── db/                              # Database setup and models
├── data/                            # Runtime uploads and generated indexes
├── frontend/                        # React/Vite application and tests
├── tests/                            # Backend unit and integration tests
├── test_*.py                        # Cross-cutting safety, API, performance, security tests
├── SECURITY.md                      # Security boundaries and disclosure guidance
└── vercel.json                      # Serverless deployment configuration
```

`main.py` serves the canonical `backend.app` API. `backend/simple_api.py` is a compatibility facade used by existing consumers and tests; it delegates to the same repositories and services. The separate `api/routes.py` SQLAlchemy/Redis application is retained as explicitly disconnected legacy code and is not registered by `main.py`, the frontend, or the Vercel deployment.

## Requirements

- Python 3.10 or newer.
- Node.js 18 or newer and npm.
- Windows, macOS, and Linux for local development.
- A Gemini-compatible API key is optional; offline mode works without one.

## Run locally

Run these commands from the directory containing this README.

### Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Start the API

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`  
OpenAPI JSON: `http://localhost:8000/openapi.json`

### Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:3000`. The frontend defaults to `http://localhost:8000`; set `VITE_API_BASE_URL` when the API runs elsewhere.

When the API is unavailable, the frontend automatically switches to synthetic browser demo mode.

## Configuration

Create a local `.env` file in the repository root when needed. Never commit it.

```dotenv
# Optional; leave empty for deterministic offline behavior.
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_TIMEOUT=90

# Force offline mode even when a key exists.
MEDLENS_OFFLINE_MODE=true

# Defaults to 10 MiB and 60 requests/minute.
MAX_UPLOAD_BYTES=10485760
MAX_REQUESTS_PER_MINUTE=60

# Comma-separated exact browser origins.
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

The backend also accepts `GOOGLE_API_KEY` and `FEATHERLESS_API_KEY` as key fallbacks. Secrets are server-only and must never be placed in frontend variables. `data/uploads` and `data/indexes` are created automatically and contain runtime state.

## Using the application

1. Start the API and frontend.
2. Create a synthetic patient from **Patient** or **+ New Patient**.
3. Add a synthetic report from **Reports** by uploading a supported file or pasting text.
4. Inspect extracted observations in **Structured Record**.
5. Use **Review** to inspect matching source excerpts and verify, edit, remove, or add observations.
6. Use **Processing & Evidence** for the observable pipeline and **Timeline** for record history.

Use synthetic or de-identified data only. Included fixtures are demonstrations, not clinical advice.

## API reference

Requests can be scoped with `X-Session-ID` or `Authorization: Bearer <session-id>`. If neither is supplied, the local demo session is used. This is prototype scoping, not authentication.

### Health

```http
GET /api/health
```

Returns non-sensitive service status and mode information.

### Patients

```http
GET    /api/patients
POST   /api/patients
GET    /api/patients/{patient_id}
PUT    /api/patients/{patient_id}
DELETE /api/patients/{patient_id}
```

Patient fields include a name plus optional age, sex, symptoms, conditions, allergies, medications, and notes.

```bash
curl -X POST http://localhost:8000/api/patients \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: local-demo" \
  -d '{"name":"Synthetic Patient","age":42,"sex":"F","conditions":[]}'
```

### Documents and ingestion

```http
GET    /api/documents?limit=20&offset=0
GET    /api/documents/{document_id}?include_chunks=false
DELETE /api/documents/{document_id}
POST   /api/documents/verify-lab
POST   /api/ingest/text
POST   /api/ingest/file
```

Text ingestion uses JSON:

```json
{
  "title": "Synthetic CBC",
  "text": "Hemoglobin: 13.5 g/dL (Ref: 12.0 - 16.0 g/dL)",
  "patient_id": "patient-id-or-null"
}
```

File ingestion uses `multipart/form-data` with `file`, optional `title`, and optional `patient_id`. Accepted extensions are `.txt`, `.pdf`, `.json`, `.html`, `.htm`, `.docx`, and `.xml`. The default limit is 10 MiB.

### Search and grounded answers

```http
POST /api/search
POST /api/ask
```

Both accept a query/question, optional `top_k`, and optional `document_id`:

```json
{
  "question": "What reference range is printed for hemoglobin?",
  "top_k": 5,
  "document_id": "optional-document-id"
}
```

Responses contain retrieved results or an answer with citations and follow-up questions. Without an LLM key, `/api/ask` returns a grounded offline snippet.

### Evidence pipeline

```http
GET  /api/documents/{document_id}/pipeline
POST /api/pipeline
POST /api/agents/sync
```

These endpoints return observable processing and provenance stages. `POST /api/agents/sync` is the platform-demo alias for the same pipeline view. Use `/docs` for exact generated schemas.

## Data and provenance model

Each observation can include its test identifier, display name, measured value, unit, source reference range, calculated status, source snippet, source location, extraction confidence, verification status, provenance type, and audit history.

Reference-range logic is conservative: when a report has no usable range, MedLens does not substitute a population range and does not label the result normal or abnormal from model assumptions.

## Safety and security

Implemented prototype controls include explicit CORS allowlisting, session-scoped records, server-side upload extension/MIME/magic-byte/size checks, UUID-based upload paths, rate limiting, PHI-oriented log redaction, prompt boundaries for untrusted report content, non-diagnostic response constraints, and deterministic offline fallback.

Important limitations remain: session IDs are caller-controlled, local storage is not encrypted at rest, there is no production identity provider, retention deletion is not a compliance control, and cloud LLM mode may transmit prompt content. Read [SECURITY.md](SECURITY.md) before deployment.

## Testing

Backend tests:

```bash
python -m pytest tests/ -v
```

Cross-cutting checks:

```bash
python -m pytest test_api.py test_clinical_safety.py test_security_hardening.py test_frontend_accessibility.py test_performance.py -v
```

Frontend tests and production build:

```bash
cd frontend
npm install
npm test
npm run build
```

Optional development tooling is pinned in `requirements-dev.txt` for Black, isort, and Flake8.

The suites cover patient intake, ingestion, extraction, reference-range safety, provenance, API behavior, session isolation, upload limits, performance, accessibility rules, and frontend workflow states. Use synthetic IDs and text in tests; never commit generated uploads, databases, logs, or keys.

## Deployment

### Frontend on Vercel

```bash
cd frontend
npm run build
npx vercel --prod
```

The Vercel target is the frontend. Set `VITE_API_BASE_URL` only to an API deployment with restricted CORS. Without a separately deployed API, the browser uses synthetic demo data.

### Before production exposure

Add OAuth2/OIDC and MFA, encrypted storage and backups, durable append-only audit logs, managed secrets, provider agreements for cloud LLM use, per-user rate limiting, monitoring, verified deletion/retention controls, and independent security, privacy, accessibility, and clinical-safety review. Never present the session header as authorization or claim regulatory compliance.

## Troubleshooting

**Demo mode appears:** Confirm the API is running on port 8000 and `VITE_API_BASE_URL` is correct.

**Upload returns `413`:** The default limit is 10 MiB; review resource and DoS implications before increasing `MAX_UPLOAD_BYTES`.

**Patient/document returns `404`:** Check the session header. Cross-session records intentionally appear as not found.

**AI is unavailable:** Configure `GEMINI_API_KEY` and verify model, base URL, timeout, and network access. Offline extraction and grounded snippets remain available.

**CORS errors:** Add the exact frontend origin, including scheme and port, to `CORS_ALLOWED_ORIGINS`, then restart the API.

**Search appears stale:** Restart the backend or rebuild generated indexes after changing runtime data. Do not edit index files while the API is running.

## Development guide

Keep API wiring in `backend/api/routes`, business behavior in `backend/services`, persistence/retrieval in `backend/repositories`, and deterministic safety/range logic independently testable. Keep frontend pages focused on presentation and user workflow. Add regression coverage for every changed safety, scoping, ingestion, or accessibility behavior. Do not log report text, names, dates of birth, or credentials.

For a new endpoint, add its router, schema, session dependency, appropriate rate limit, and tests for both success and cross-session access.

## Limitations and roadmap

MedLens is intentionally a prototype. Next steps include real identity and role-based access control, encrypted managed storage, durable audit/retention services, richer citations, background ingestion jobs, broader OCR evaluation, measured model evaluation sets, automated browser accessibility checks, observability, and incident response.

## License and responsible disclosure

No license is asserted by this README. Confirm repository ownership and licensing requirements before redistribution. For security concerns, follow the private disclosure guidance in [SECURITY.md](SECURITY.md); do not publish exploitable details or real clinical data in an issue.

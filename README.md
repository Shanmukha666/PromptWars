# MedLens — Clinical Intelligence Copilot with Google Gemini

This version keeps the original logic intact:

1. ingest documents
2. index chunks
3. run semantic search
4. ask grounded questions

It adds the hackathon layer on top:

- visible agent orchestration
- simulation mode for lab values
- evidence cards for explainability
- API demo panel for platform storytelling
- offline fallback mode so the app still works without a Google Gemini key

## What changed

### Frontend
- redesigned as a hackathon demo dashboard
- added agent workflow timeline
- added simulation controls for hemoglobin, WBC, and platelets
- added API demo panel with ready-to-use curl examples
- preserved document ingestion, semantic search, grounded QA, and document inspection

### Backend
- added `POST /api/agents/sync`
- added deterministic multi-agent orchestration output:
  - ingestion agent
  - retrieval agent
  - safety validation agent
  - validation agent
  - critic agent
  - explanation agent
- added offline summary and QA fallbacks when `GEMINI_API_KEY` is missing
- preserved the original endpoints:
  - `GET /api/health`
  - `GET /api/documents`
  - `GET /api/documents/{document_id}`
  - `POST /api/ingest/text`
  - `POST /api/ingest/file`
  - `POST /api/search`
  - `POST /api/ask`

## Run locally

### Backend
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Running Tests

The test suite covers backend clinical safety, extraction boundaries, reference interval rules, session security, and frontend workflow components.

### Backend Tests (pytest)
```bash
# Run all backend tests
python -m pytest tests/ -v
```

### Frontend Tests (Vitest + Testing Library)
```bash
# Run all frontend tests
cd frontend
npm test
```

## Environment

Optional for live LLM mode:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=https://api.featherless.ai/v1
```

Without a key, the app uses offline heuristic fallback logic so the demo still runs.

## Vercel preview deployment

The Vercel target is the frontend only. Without a separately deployed API, the browser uses bundled synthetic demo records. Set `VITE_API_BASE_URL` only for an API deployed with restricted CORS. Never expose `GEMINI_API_KEY` or backend secrets to the browser.

```bash
cd frontend
npm run build
npx vercel --prod
```

This prototype does not provide production identity authentication, encrypted-at-rest storage, retention deletion, or regulatory compliance. Use synthetic or de-identified data only.

## Hackathon pitch angle

> We did not just build a RAG app. We built a clinical intelligence copilot where specialized agents retrieve evidence, propose a diagnosis, validate it, challenge it, and then explain it — all while exposing APIs that make the whole system reusable as a platform.

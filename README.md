# Research Multi-Agent Workflow

A local-first research brief application demonstrating a small, auditable multi-agent workflow.

## Workflow

1. Validate and scope the request.
2. Plan focused research queries.
3. Gather sources.
4. Extract source-linked evidence.
5. Synthesize a cited brief.
6. Review citation references.

The React + TypeScript frontend is in `research-brief-web/`. The FastAPI + LangGraph backend is in `research-brief-api/`.

## Run locally

Start the backend in one terminal:

```powershell
cd research-brief-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```powershell
cd research-brief-web
npm install
npm run dev
```

The backend uses deterministic mock mode by default. No `.env` file or API key is needed for the local demo. Optional provider credentials belong in a local ignored `.env` file and must never be committed.

## Current scope

This v1 prototype uses in-memory runs and does not include authentication or tenant isolation. Production work identified for a next phase includes database persistence, tenant isolation, authentication, human review, per-step visualization, recoverable/resumable runs, citation reranking, frontier model evaluation, and deployment.

See `output/` for the architecture and validation report.

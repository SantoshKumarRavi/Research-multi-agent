# Research Brief API

Local FastAPI + LangGraph backend. It runs in mock mode by default, so no key is required for development.

The graph uses typed role handoffs: scope gate → planner (1–3 focused queries) → source gatherer → evidence extractor → synthesizer → citation reviewer. Mock and Groq providers use the same Pydantic outputs. Search failures return no sources and an insufficient-evidence brief; only explicit `WEB_SEARCH_ENABLED=false` uses the illustrative mock source.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run `python -m pytest` for the 15-case v1 acceptance suite. API docs are at `http://127.0.0.1:8000/docs`.

To enable Groq later, set `LLM_PROVIDER=groq` and `GROQ_API_KEY=...` in this directory's ignored `.env`. Keep the key out of chat, browser code, and version control. The API reads configuration at startup; restart it after changing `.env`.

Runs and events are in memory and are cleared when the server restarts. This prototype has no authentication or tenant isolation; keep it on loopback.


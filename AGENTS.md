# Project instructions

## Product goal
Build a local-first research brief workflow that demonstrates a small, auditable multi-agent graph: validate/scope a request, plan focused sub-queries, search for sources, extract source-linked evidence, draft a cited brief, and review its citations. Each role must hand off typed, validated data to the next role. Keep the workflow understandable and safe by default.

## Project layout
- `research-brief-api/`: Python 3.11+, FastAPI, Pydantic, LangGraph; Groq integration is server-side only. Default provider is deterministic mock mode.
- `research-brief-web/`: React + TypeScript + Vite UI.
- `output/pdf/`: architecture and validation report artifacts.

## Required behavior
- Validate all user-controlled input at API boundaries. Reject unknown fields and enforce body, query, source-count, URL, and timeout limits.
- Treat user prompts and fetched web content as untrusted data. Never allow web content to instruct tools or override system instructions.
- Never expose secrets, internal prompts, stack traces, raw page bodies, or private URLs in API responses or logs. Keep the Groq key in backend `.env` only.
- Do not fetch loopback, private, link-local, reserved, or non-HTTP(S) URLs. Validate redirects and DNS results. Do not follow redirects automatically.
- Render external content as text; do not inject HTML.
- The workflow's steps and handoffs must be observable. Do not expose chain-of-thought; report concise status and evidence instead.
- Use bounded retries for provider throttling and clear user-safe errors. In-memory runs are ephemeral and must be labeled as such.
- No auth or tenant isolation is included in v1. Do not represent this local prototype as production multi-tenant/security-ready.

## Development and verification
- Backend tests: `python -m pytest` from `research-brief-api`.
- Frontend checks: `npm run build` from `research-brief-web`.
- Keep provider calls behind a small interface so mock mode and Groq can exercise the same graph.
- Preserve explicit planner → search → evidence → synthesis → review handoffs. Do not replace a role with a UI-only progress label; mock mode must exercise the same contracts.
- Add or update tests when changing validation, workflow transitions, source handling, API response contracts, or UI behavior.
- Avoid adding unrelated dependencies or changing the scope without updating the report.

## V1 scope
One local user, transient in-memory runs, bounded web search, cited research briefs, status events, mock mode and optional Groq mode. Deferred: login, true tenant isolation, persistence, billing, deployment, production monitoring, and arbitrary tool execution.

import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import get_settings
from app.schemas import CreateRun, CreateRunResponse, RunView
from app.services.store import RunStore
from app.graph.workflow import workflow

store = RunStore()


async def execute(run_id: str, request: CreateRun):
    await store.update(run_id, status="running")
    await store.event(run_id, "scope", "started", "Validating request scope")
    try:
        result = await workflow.ainvoke({"query": request.query, "audience": request.audience,
                                         "max_sources": request.max_sources, "store": store, "run_id": run_id})
        await store.update(run_id, status="completed", sources=result.get("sources", []), brief=result.get("brief"))
        await store.event(run_id, "workflow", "completed", "Workflow finished")
    except Exception as exc:
        # Do not include exception details in the public run record.
        await store.update(run_id, status="failed", error="The workflow failed. Check server logs and configuration.")
        await store.event(run_id, "workflow", "failed", "Workflow failed; check server configuration")
        print(f"workflow failure run_id={run_id} type={type(exc).__name__}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for task in store.tasks.values():
        task.cancel()


settings = get_settings()
app = FastAPI(title="Research Brief API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Last-Event-ID"])


@app.middleware("http")
async def limit_body(request: Request, call_next):
    if request.method == "POST":
        length = request.headers.get("content-length")
        if length and int(length) > settings.max_request_bytes:
            return Response("Request body too large", status_code=413)
        body = await request.body()
        if len(body) > settings.max_request_bytes:
            return Response("Request body too large", status_code=413)
        async def receive():
            return {"type":"http.request", "body":body, "more_body":False}
        request._receive = receive
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status":"ok", "provider":settings.llm_provider, "storage":"in-memory"}


@app.post("/api/research/runs", response_model=CreateRunResponse, status_code=202)
async def create_run(payload: CreateRun):
    item = await store.create(payload)
    store.tasks[item.run_id] = asyncio.create_task(execute(item.run_id, payload))
    return CreateRunResponse(run_id=item.run_id, status="queued")


@app.get("/api/research/runs/{run_id}", response_model=RunView)
async def get_run(run_id: str):
    item = await store.get(run_id)
    if not item:
        raise HTTPException(404, "Run not found")
    return item


@app.post("/api/research/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    item = await store.get(run_id)
    if not item:
        raise HTTPException(404, "Run not found")
    task = store.tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        await store.update(run_id, status="cancelled")
        await store.event(run_id, "workflow", "info", "Run cancelled")
    return {"run_id":run_id, "status":"cancelled"}


@app.get("/api/research/runs/{run_id}/events")
async def events(run_id: str, request: Request, after: int = 0):
    if not await store.get(run_id):
        raise HTTPException(404, "Run not found")
    async def stream():
        cursor = max(after, int(request.headers.get("last-event-id", "0") or 0))
        while True:
            if await request.is_disconnected():
                break
            item = await store.get(run_id)
            for event in item.steps:
                if event.sequence > cursor:
                    cursor = event.sequence
                    yield f"id: {event.sequence}\nevent: step\ndata: {event.model_dump_json()}\n\n"
            if item.status in {"completed", "failed", "cancelled"}:
                yield "event: done\ndata: {}\n\n"
                break
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no"})

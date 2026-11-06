import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from app.schemas import RunEvent, RunView, CreateRun


class RunStore:
    def __init__(self):
        self.runs: dict[str, RunView] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()

    async def create(self, request: CreateRun) -> RunView:
        now = datetime.now(timezone.utc)
        item = RunView(run_id=str(uuid4()), status="queued", query=request.query,
                       audience=request.audience, created_at=now, updated_at=now, steps=[])
        async with self.lock:
            self.runs[item.run_id] = item
        return item

    async def get(self, run_id: str) -> RunView | None:
        async with self.lock:
            item = self.runs.get(run_id)
            return item.model_copy(deep=True) if item else None

    async def update(self, run_id: str, **changes):
        async with self.lock:
            item = self.runs.get(run_id)
            if not item:
                return
            for key, value in changes.items():
                setattr(item, key, value)
            item.updated_at = datetime.now(timezone.utc)

    async def event(self, run_id: str, node: str, status: str, message: str):
        async with self.lock:
            item = self.runs.get(run_id)
            if not item:
                return
            seq = len(item.steps) + 1
            item.steps.append(RunEvent(event_id=seq, sequence=seq, run_id=run_id,
                                       timestamp=datetime.now(timezone.utc), node=node,
                                       status=status, message=message))
            item.updated_at = datetime.now(timezone.utc)

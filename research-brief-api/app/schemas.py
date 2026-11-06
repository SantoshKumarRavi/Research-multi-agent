from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import unicodedata


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateRun(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    max_sources: int = Field(default=5, ge=1, le=10, strict=True)
    audience: Literal["general", "technical", "executive"] = "general"

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value):
        if not isinstance(value, str):
            raise ValueError("query must be text")
        value = unicodedata.normalize("NFKC", value).strip()
        if any(unicodedata.category(ch) in {"Cc", "Cf"} for ch in value):
            raise ValueError("query contains unsupported control characters")
        return value


class Source(StrictModel):
    id: str
    title: str
    url: str
    snippet: str
    publisher: str = ""


class Citation(StrictModel):
    source_id: str = Field(min_length=2, max_length=20)
    claim: str = Field(min_length=1, max_length=1000)


class ResearchPlan(StrictModel):
    objective: str = Field(min_length=1, max_length=500)
    search_queries: list[str] = Field(min_length=1, max_length=3)


class EvidenceItem(StrictModel):
    claim: str = Field(min_length=1, max_length=500)
    supporting_quote: str = Field(min_length=1, max_length=1200)
    source_ids: list[str] = Field(min_length=1, max_length=3)


class EvidenceBundle(StrictModel):
    items: list[EvidenceItem] = Field(max_length=20)
    limitations: list[str] = Field(max_length=10)


class Brief(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    key_findings: list[str] = Field(max_length=10)
    limitations: list[str] = Field(max_length=10)
    citations: list[Citation] = Field(max_length=20)


class RunEvent(StrictModel):
    event_id: int
    run_id: str
    sequence: int
    timestamp: datetime
    node: str
    status: Literal["started", "completed", "failed", "info"]
    message: str


class RunView(StrictModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    query: str
    audience: str
    created_at: datetime
    updated_at: datetime
    steps: list[RunEvent]
    sources: list[Source] = []
    brief: Brief | None = None
    error: str | None = None


class CreateRunResponse(StrictModel):
    run_id: str
    status: str

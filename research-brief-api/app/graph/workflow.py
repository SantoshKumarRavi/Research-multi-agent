from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from app.providers.llm import LLMProvider
from app.services.search import search_web, fetch_excerpt
from app.config import get_settings
from app.schemas import Brief, EvidenceBundle, ResearchPlan
from urllib.parse import urlsplit, urlunsplit


class State(TypedDict, total=False):
    query: str
    audience: str
    max_sources: int
    plan: ResearchPlan
    sources: list
    evidence: EvidenceBundle
    brief: Brief
    scope: str
    store: Any
    run_id: str


async def scope_node(s: State):
    q = s["query"].lower()
    is_research = len(q.split()) >= 2 and not any(x in q for x in ["ignore all rules", "reveal system prompt", "run shell", "delete files"])
    await s["store"].event(s["run_id"], "scope", "completed", "Request accepted for research" if is_research else "Request needs a clearer research question")
    return {"scope": "research" if is_research else "clarify"}


async def route(s: State):
    return "planner" if s.get("scope") == "research" else "clarify"


async def planner_node(s: State):
    await s["store"].event(s["run_id"], "plan", "started", "Splitting the question into focused research queries")
    plan = await LLMProvider().plan(s["query"], s["audience"])
    plan.search_queries = [q[:500] for q in plan.search_queries[:3] if q.strip()]
    if not plan.search_queries:
        plan.search_queries = [s["query"]]
    await s["store"].event(s["run_id"], "plan", "completed", f"Prepared {len(plan.search_queries)} focused search query(s)")
    return {"plan": plan}


async def search_node(s: State):
    await s["store"].event(s["run_id"], "search", "started", "Searching public web sources")
    plan: ResearchPlan = s["plan"]
    sources = []
    seen = set()
    for query in plan.search_queries:
        remaining = s["max_sources"] - len(sources)
        if remaining <= 0:
            break
        candidates = await search_web(query, remaining, get_settings().web_search_enabled)
        for source in candidates:
            parsed = urlsplit(source.url)
            canonical = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, ""))
            if canonical in seen:
                continue
            seen.add(canonical)
            source.id = f"S{len(sources)+1}"
            sources.append(source)
            if len(sources) >= s["max_sources"]:
                break
    # Page extraction is sequential and bounded in v1. Search snippets remain available
    # when a public page blocks fetching or times out.
    enriched = []
    for source in sources[:3]:
        if not source.snippet.startswith("Mock source used"):
            try:
                excerpt = await fetch_excerpt(source.url)
                if excerpt:
                    source.snippet = (source.snippet + "\n" + excerpt[:2500])[:4000]
            except Exception:
                pass
        enriched.append(source)
    sources = enriched + sources[3:]
    await s["store"].update(s["run_id"], sources=sources)
    await s["store"].event(s["run_id"], "search", "completed", f"Collected {len(sources)} source(s)")
    return {"sources": sources}


async def extract_node(s: State):
    await s["store"].event(s["run_id"], "evidence", "started", "Extracting evidence with source-linked handoffs")
    evidence = await LLMProvider().extract(s["query"], s.get("sources", []))
    allowed = {source.id for source in s.get("sources", [])}
    evidence.items = [item for item in evidence.items if item.source_ids and set(item.source_ids).issubset(allowed)][:20]
    await s["store"].event(s["run_id"], "evidence", "completed", f"Prepared {len(evidence.items)} source-linked evidence item(s)")
    return {"evidence": evidence}


async def synthesize_node(s: State):
    await s["store"].event(s["run_id"], "synthesis", "started", "Drafting cited brief")
    evidence = s.get("evidence", EvidenceBundle(items=[], limitations=[]))
    if evidence.items:
        brief = await LLMProvider().summarize(s["query"], s["audience"], evidence)
    else:
        from app.schemas import Brief
        brief = Brief(title=f"Research brief: {s['query'][:100]}",
                      summary="No source-backed evidence was collected. Refine the question or retry when search is available.",
                      key_findings=[], limitations=["No usable source evidence was returned.", *evidence.limitations[:5]], citations=[])
    await s["store"].event(s["run_id"], "synthesis", "completed", "Drafted research brief")
    return {"brief": brief}


async def review_node(s: State):
    await s["store"].event(s["run_id"], "review", "started", "Validating brief citations against evidence and source records")
    brief: Brief = s["brief"]
    allowed = {source.id for source in s.get("sources", [])}
    evidence_sources = {source_id for item in s.get("evidence", EvidenceBundle(items=[], limitations=[])).items for source_id in item.source_ids}
    brief.citations = [c for c in brief.citations if c.source_id in allowed and c.source_id in evidence_sources]
    await s["store"].event(s["run_id"], "review", "completed", f"Validated {len(brief.citations)} source-linked citation(s)")
    return {"brief": brief}


async def clarify_node(s: State):
    await s["store"].event(s["run_id"], "clarify", "completed", "Please provide a specific research question")
    return {"brief": None, "sources": []}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("scope", scope_node)
    graph.add_node("planner", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("evidence", extract_node)
    graph.add_node("synthesis", synthesize_node)
    graph.add_node("review", review_node)
    graph.add_node("clarify", clarify_node)
    graph.set_entry_point("scope")
    graph.add_conditional_edges("scope", route, {"planner":"planner", "clarify":"clarify"})
    graph.add_edge("planner", "search")
    graph.add_edge("search", "evidence")
    graph.add_edge("evidence", "synthesis")
    graph.add_edge("synthesis", "review")
    graph.add_edge("review", END)
    graph.add_edge("clarify", END)
    return graph.compile()


workflow = build_graph()

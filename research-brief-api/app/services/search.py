import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from app.schemas import Source


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Private destinations are not allowed")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError("Host could not be resolved") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("Private destinations are not allowed")
    return url


async def search_web(query: str, count: int, enabled: bool) -> list[Source]:
    if not enabled:
        return mock_sources(query, count)
    def search():
        return list(DDGS().text(query, max_results=count))
    try:
        raw = await asyncio.wait_for(asyncio.to_thread(search), timeout=12)
    except Exception:
        return []
    results = []
    for i, row in enumerate(raw[:count]):
        url = row.get("href") or row.get("url") or ""
        try:
            validate_public_url(url)
        except ValueError:
            continue
        results.append(Source(id=f"S{i+1}", title=str(row.get("title") or "Untitled")[:300],
                              url=url, snippet=str(row.get("body") or "")[:2000],
                              publisher=urlparse(url).hostname or ""))
    return results


def mock_sources(query: str, count: int) -> list[Source]:
    safe = query.replace("<", "").replace(">", "")[:90]
    return [Source(id="S1", title=f"Research starting point: {safe}", url="https://www.who.int/",
                   snippet="Mock source used in local evaluation. Replace with enabled web search for live research.",
                   publisher="World Health Organization")][:count]


async def fetch_excerpt(url: str) -> str:
    validate_public_url(url)
    timeout = httpx.Timeout(6, connect=3)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": "ResearchBriefBot/1.0"}) as client:
        current = url
        for _ in range(4):
            validate_public_url(current)
            async with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        break
                    from urllib.parse import urljoin
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                if int(response.headers.get("content-length", "0") or 0) > 1_000_000:
                    raise ValueError("Page is too large")
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_000_000:
                        raise ValueError("Page is too large")
                    chunks.append(chunk)
                raw_text = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
            soup = BeautifulSoup(raw_text, "html.parser")
            for el in soup(["script", "style", "nav", "footer", "header"]):
                el.decompose()
            return soup.get_text(" ", strip=True)[:5000]
    return ""

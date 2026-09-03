import httpx

from .config import settings


async def list_entries(content_type: str | None = None, page: int = 1, page_size: int = 5) -> list[dict]:
    params = {"page": page, "page_size": min(page_size, 5)}
    if content_type:
        params["content_type"] = content_type
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/entries", params=params)
        response.raise_for_status()
        entries = response.json()
        # Keep tool context small; the model only needs public display fields to answer questions.
        return [
            {
                "type": entry.get("content_type"),
                "title": entry.get("title"),
                "blurb": entry.get("blurb"),
                "date": entry.get("date"),
                "tags": entry.get("tags", []),
                "url": entry.get("links", {}).get("url"),
            }
            for entry in entries
        ]


async def get_profile() -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/profile")
        response.raise_for_status()
        return response.json()


async def search_portfolio(query: str, page: int = 1) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/search", params={"q": query, "page": page, "page_size": 5})
        response.raise_for_status()
        result = response.json()
        return {"profile": result.get("profile"), "entries": [{"type": item.get("content_type"), "title": item.get("title"), "blurb": item.get("blurb"), "date": item.get("date"), "tags": item.get("tags", []), "url": item.get("links", {}).get("url")} for item in result.get("entries", [])]}


TOOLS = [{
    "type": "function",
    "function": {
        "name": "list_entries",
        "description": "List public portfolio entries. Use this before answering facts about Mike's work.",
        "parameters": {"type": "object", "properties": {"content_type": {"type": "string", "enum": ["project", "article", "hackathon", "event"]}, "page": {"type": "integer", "minimum": 1, "default": 1}}, "required": []},
    },
}, {
    "type": "function",
    "function": {
        "name": "get_profile",
        "description": "Get verified public profile information about Michael Odhiambo.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}, {
    "type": "function",
    "function": {
        "name": "search_portfolio",
        "description": "Search all public portfolio content and profile information. Use this first for broad or ambiguous questions.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "default": 1}}, "required": ["query"]},
    },
}]


async def execute_tool(name: str, arguments: dict):
    if name == "get_profile":
        return await get_profile()
    if name == "search_portfolio":
        return await search_portfolio(arguments["query"], arguments.get("page", 1))
    if name != "list_entries":
        raise ValueError(f"Unknown tool: {name}")
    return await list_entries(arguments.get("content_type"), arguments.get("page", 1))

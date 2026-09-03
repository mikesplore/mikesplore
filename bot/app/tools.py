import httpx

from .config import settings


async def list_entries(content_type: str | None = None) -> list[dict]:
    params = {"content_type": content_type} if content_type else {}
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
            for entry in entries[:20]
        ]


TOOLS = [{
    "type": "function",
    "function": {
        "name": "list_entries",
        "description": "List public portfolio entries. Use this before answering facts about Mike's work.",
        "parameters": {"type": "object", "properties": {"content_type": {"type": "string", "enum": ["project", "article", "hackathon", "event"]}}, "required": []},
    },
}]


async def execute_tool(name: str, arguments: dict):
    if name != "list_entries":
        raise ValueError(f"Unknown tool: {name}")
    return await list_entries(arguments.get("content_type"))

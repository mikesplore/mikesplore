import httpx

from .config import settings


async def list_entries(content_type: str | None = None, page: int = 1, page_size: int = 5) -> dict:
    params = {"page": page, "page_size": min(page_size, 5)}
    if content_type:
        params["content_type"] = content_type
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/entries", params=params)
        response.raise_for_status()
        entries = response.json()
        total = int(response.headers.get("x-total-count", len(entries)))
        # Keep tool context small; the model only needs public display fields to answer questions.
        return {"total": total, "page": page, "page_size": len(entries), "entries": [
            {
                "type": entry.get("content_type"),
                "slug": entry.get("slug"),
                "title": entry.get("title"),
                "blurb": entry.get("blurb"),
                "date": entry.get("date"),
                "tags": entry.get("tags", []),
                "url": (entry.get("source") or {}).get("key") or entry.get("links", {}).get("url"),
            }
            for entry in entries
        ]}


async def get_profile() -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/profile")
        response.raise_for_status()
        return response.json()


async def list_certificates(query: str = "") -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/certificates")
        response.raise_for_status()
        certificates = response.json()
        needle = query.strip().casefold()
        if needle:
            certificates = [item for item in certificates if needle in item.get("title", "").casefold()]
        return [{"title": item["title"], "certificate_id": item["id"], "image_url": item.get("image_url")} for item in certificates]


async def list_public_assets(asset_type: str | None = None) -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/assets")
        response.raise_for_status()
        assets = response.json()
        if asset_type:
            assets = [item for item in assets if item.get("asset_type") == asset_type]
        return [{"id": item.get("id"), "type": item.get("asset_type"), "label": item.get("label"), "url": item.get("url")} for item in assets]


async def list_skills() -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/skills")
        response.raise_for_status()
        return [{"category": item["category"], "skills": item["skills"]} for item in response.json()]


async def list_contact_links() -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/profile/links")
        response.raise_for_status()
        return [{"name": item["name"], "url": item["url"], "label": item.get("label"), "handle": item.get("handle"), "category": item.get("category")} for item in response.json()]

async def get_entry_by_slug(slug: str) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get(f"/entries/slug/{slug}")
        if response.status_code == 404:
            return {"found": False, "slug": slug}
        response.raise_for_status()
        entry = response.json()
        source = entry.get("source") or {}
        body = source.get("body_markdown") or source.get("body_html") or ""
        return {"found": True, **{key: entry.get(key) for key in ("slug", "content_type", "title", "blurb", "date", "year", "tags", "tech_stack", "details", "links")}, "url": source.get("key"), "article_body": body[:12000]}


async def request_cv_delivery() -> dict:
    return {"action": "send_cv"}


async def request_certificate_delivery(query: str = "") -> dict:
    return {"action": "send_certificates", "query": query}


async def request_owner_unlock(action: str = "") -> dict:
    return {"action": "request_owner_unlock", "requested_action": action[:120]}


async def search_cv(query: str) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/cv/search", params={"q": query})
        response.raise_for_status()
        return response.json()


async def search_portfolio(query: str, page: int = 1) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/search", params={"q": query, "page": page, "page_size": 5})
        response.raise_for_status()
        result = response.json()
        return {"profile": result.get("profile"), "total": result.get("total", 0), "page": result.get("page", page), "page_size": result.get("page_size", 5), "entries": [{"slug": item.get("slug"), "type": item.get("content_type"), "title": item.get("title"), "blurb": item.get("blurb"), "date": item.get("date"), "tags": item.get("tags", []), "url": (item.get("source") or {}).get("key") or item.get("links", {}).get("url")} for item in result.get("entries", [])], "certificates": [{"type": "certificate", "title": item.get("title")} for item in result.get("certificates", [])], "skills": result.get("skills", []), "links": [{"name": item.get("name"), "url": item.get("url")} for item in result.get("links", [])], "education": [{"degree": item.get("degree"), "school": item.get("school")} for item in result.get("education", [])], "bucket_list": [{"title": item.get("title"), "done": item.get("done")} for item in result.get("bucket_list", [])]}


async def search_articles(query: str, page: int = 1) -> dict:
    result = await search_portfolio(query, page)
    articles = [entry for entry in result.get("entries", []) if entry.get("type") == "article"]
    return {"total": len(articles), "page": page, "articles": articles}


async def list_articles(page: int = 1) -> dict:
    result = await list_entries("article", page)
    return {"total": result["total"], "page": result["page"], "articles": result["entries"]}


TOOLS = [{
    "type": "function",
    "function": {"name": "get_entry_by_slug", "description": "Get one verified visible portfolio entry by its exact slug.", "parameters": {"type": "object", "properties": {"slug": {"type": "string"}}, "required": ["slug"]}},
}, {
    "type": "function",
    "function": {"name": "list_articles", "description": "List only public synced Dev.to articles. Never substitute projects or other entry types.", "parameters": {"type": "object", "properties": {"page": {"type": "integer", "minimum": 1, "default": 1}}, "required": []}},
}, {
    "type": "function",
    "function": {
        "name": "list_entries",
        "description": "List public portfolio entries. Use this before answering facts about Mike's work.",
        "parameters": {"type": "object", "properties": {"content_type": {"type": "string", "enum": ["project", "article", "hackathon", "event"]}, "page": {"type": "integer", "minimum": 1, "default": 1}}, "required": []},
    },
}, {
    "type": "function",
    "function": {"name": "search_articles", "description": "Search only synced public Dev.to articles by title, tags, description, or full article body. Never return projects for an article question.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "default": 1}}, "required": ["query"]}},
}, {
    "type": "function",
    "function": {"name": "request_cv_delivery", "description": "Send the portfolio owner's verified CV file directly to the user when they ask to see, view, download, share, attach, or receive it.", "parameters": {"type": "object", "properties": {}, "required": []}},
}, {
    "type": "function",
    "function": {"name": "request_certificate_delivery", "description": "Send verified certificate files directly to the user when they ask to see or receive certificates. Include a title or keyword query when the user asks for a specific certificate.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": []}},
}, {
    "type": "function",
    "function": {"name": "list_contact_links", "description": "List all verified public professional and social contact links for the portfolio owner. Use this for contact, social media, or how-to-reach-the-owner questions.", "parameters": {"type": "object", "properties": {}, "required": []}},
}, {
    "type": "function",
    "function": {"name": "search_cv", "description": "Search verified text extracted from the portfolio owner's uploaded CV.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
}, {
    "type": "function",
    "function": {"name": "list_skills", "description": "List verified skills from the public portfolio database.", "parameters": {"type": "object", "properties": {}, "required": []}},
}, {
    "type": "function",
    "function": {
        "name": "get_profile",
        "description": "Get verified public profile information about the portfolio owner.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}, {
    "type": "function",
    "function": {
        "name": "search_portfolio",
        "description": "Search all public portfolio content and profile information. Use this first for broad or ambiguous questions.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "default": 1}}, "required": ["query"]},
    },
}, {
    "type": "function",
    "function": {"name": "list_certificates", "description": "List available public certificates. Include a title keyword when the user asks for one specific certificate; otherwise list all.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": []}},
}, {
    "type": "function",
    "function": {"name": "list_public_assets", "description": "List verified public portfolio media. Set asset_type to profile-image for a profile picture, cv for a CV, or certificate for a certificate.", "parameters": {"type": "object", "properties": {"asset_type": {"type": "string", "enum": ["profile-image", "cv", "certificate"]}}, "required": []}},
}, {
    "type": "function",
    "function": {"name": "request_owner_unlock", "description": "Request owner verification before a profile, CV, media, or portfolio update. Use this for any admin or mutation request. This only reveals the PIN prompt; it never performs the update.", "parameters": {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]}},
}]


async def execute_tool(name: str, arguments: dict):
    if name == "get_profile":
        return await get_profile()
    if name == "list_certificates":
        return await list_certificates(arguments.get("query", ""))
    if name == "list_public_assets":
        return await list_public_assets(arguments.get("asset_type"))
    if name == "list_skills":
        return await list_skills()
    if name == "list_contact_links":
        return await list_contact_links()
    if name == "get_entry_by_slug":
        return await get_entry_by_slug(arguments["slug"])
    if name == "request_cv_delivery":
        return await request_cv_delivery()
    if name == "request_certificate_delivery":
        return await request_certificate_delivery(arguments.get("query", ""))
    if name == "request_owner_unlock":
        return await request_owner_unlock(arguments.get("action", ""))
    if name == "search_cv":
        return await search_cv(arguments["query"])
    if name == "search_portfolio":
        return await search_portfolio(arguments["query"], arguments.get("page", 1))
    if name == "search_articles":
        return await search_articles(arguments["query"], arguments.get("page", 1))
    if name == "list_articles":
        return await list_articles(arguments.get("page", 1))
    if name != "list_entries":
        raise ValueError(f"Unknown tool: {name}")
    return await list_entries(arguments.get("content_type"), arguments.get("page", 1))

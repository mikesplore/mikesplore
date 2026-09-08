import json

from ..admin import list_admin_resource, list_profile_links, search_admin_content, sync_devto_articles

ADMIN_TOOLS = [
    {"type": "function", "function": {"name": "list_profile_links", "description": "List all existing contact and social profile links before updating or deleting one.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_assets", "description": "List uploaded portfolio assets with IDs, labels, and URLs.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_projects", "description": "List project entries with IDs, slugs, and titles.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_repositories", "description": "List existing repositories with IDs, entry IDs, names, and URLs before creating or updating one.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "find_repository", "description": "Find an existing repository by its exact URL before deciding between create and update.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "list_technologies", "description": "List normalized technologies with IDs and names.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "search_admin_content", "description": "Search existing admin-managed portfolio records when the requested record is not a contact link.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "request_upload", "description": "Request a file from the administrator. Use for profile images, certificates, CVs, project images, or other project media. Include the exact asset type and, for project media, the resolved entry_id and role.", "parameters": {"type": "object", "properties": {"asset_type": {"type": "string", "enum": ["profile-image", "certificate", "cv", "project-image", "project-media"]}, "label": {"type": "string"}, "entry_id": {"type": "string"}, "role": {"type": "string"}}, "required": ["asset_type"]}}},
    {"type": "function", "function": {"name": "request_cv_tailoring", "description": "Recognize a bare job description from the portfolio owner and start CV tailoring. Pass the complete job description exactly as provided. Do not use this for ordinary portfolio questions.", "parameters": {"type": "object", "properties": {"job_description": {"type": "string"}}, "required": ["job_description"]}}},
    {"type": "function", "function": {"name": "propose_role_policies", "description": "Analyze the verified CV context and propose pending role-family policies for CV tailoring. Never activate policies and never invent evidence.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "list_role_policies", "description": "List role policies with exact IDs and activation status before activating or revising them.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "sync_devto_articles", "description": "Sync the owner's published Dev.to articles into the portfolio, including their full public body for grounded article explanations.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "create_admin_operation", "description": "Return only the final structured admin operation after lookups. For action=list, payload MUST be {} and must never contain lookup results. Do not explain it in text.", "parameters": {"type": "object", "properties": {"resource": {"type": "string"}, "action": {"type": "string", "enum": ["list", "create", "update", "delete", "propose"]}, "id": {"type": "string"}, "payload": {"type": "object"}}, "required": ["resource", "action", "payload"]}}},
]

async def execute_admin_tool(name: str, arguments: dict, admin_authorized: bool = False) -> list[dict]:
    if not admin_authorized:
        raise PermissionError("Admin tools are restricted to the portfolio owner.")
    if name == "list_profile_links":
        return await list_profile_links()
    if name == "list_assets":
        return [{key: item.get(key) for key in ("id", "asset_type", "url", "label")} for item in (await list_admin_resource("assets"))[:10]]
    if name == "list_projects":
        return [{key: item.get(key) for key in ("id", "slug", "title", "content_type")} for item in (await list_admin_resource("entries")) if item.get("content_type") == "project"][:10]
    if name == "list_repositories":
        return [{key: item.get(key) for key in ("id", "entry_id", "name", "url", "is_visible", "is_primary", "role_label", "primary_language", "link_label")} for item in (await list_admin_resource("repositories"))[:10]]
    if name == "find_repository":
        url = arguments.get("url", "").strip().lower().rstrip("/")
        records = await list_admin_resource("repositories")
        return [{key: item.get(key) for key in ("id", "entry_id", "name", "url", "is_visible", "is_primary", "role_label", "primary_language", "link_label")} for item in records if str(item.get("url", "")).strip().lower().rstrip("/") == url]
    if name == "list_technologies":
        return [{key: item.get(key) for key in ("id", "name", "category", "icon_url")} for item in (await list_admin_resource("technologies"))[:50]]
    if name == "search_admin_content":
        results = await search_admin_content(arguments.get("query", ""))
        return [{"resource": item.get("resource"), "score": item.get("score"), "record": {key: value for key, value in (item.get("record") or {}).items() if key in {"id", "slug", "name", "title", "url", "label", "handle", "asset_type", "content_type"}}} for item in results[:10]]
    if name == "create_admin_operation":
        return arguments
    if name == "request_upload":
        return {"resource": "uploads", "action": "request", "payload": arguments}
    if name == "request_cv_tailoring":
        return {"resource": "cv-tailoring", "action": "request", "payload": arguments}
    if name == "propose_role_policies":
        from .orchestration import propose_role_policies
        return {"resource": "role-policies", "action": "propose", "payload": {"policies": await propose_role_policies()}}
    if name == "list_role_policies":
        return [{key: item.get(key) for key in ("id", "role_family", "titles", "status", "is_active", "confidence")} for item in await list_admin_resource("role-policies")]
    if name == "sync_devto_articles":
        return {"resource": "devto-sync", "action": "request", "payload": await sync_devto_articles()}
    raise ValueError(f"Unsupported admin lookup tool: {name}")

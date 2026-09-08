"""Execution of already-authorized administrator mutations."""


async def execute_admin_operation(operation: dict, *, update_profile, manage_content, bulk_manage_links) -> str:
    """Apply one operation after authorization and any confirmation have completed."""
    resource, action = operation["resource"], operation["action"]
    if resource == "profile":
        await update_profile(operation.get("payload", {}))
    else:
        payload = dict(operation.get("payload") or {key: value for key, value in operation.items() if key not in {"resource", "action", "id", "candidates", "payload"}})
        if operation.get("id"):
            payload["id"] = operation["id"]
        values = payload.get("links") if resource == "links" else payload.get("technologies") if resource == "entry-technologies" else None
        if isinstance(values, list):
            if resource == "links":
                await bulk_manage_links([{"action": action, "id": item.get("id"), "payload": {key: value for key, value in item.items() if key != "id"}} for item in values])
            else:
                for item in values:
                    await manage_content(resource, action, {"entry_id": payload.get("entry_id"), **item})
        else:
            await manage_content(resource, action, payload)
    return {"create": f"{resource.title()} created.", "update": f"{resource.title()} updated.", "delete": f"{resource.title()} deleted."}.get(action, "Change applied.")

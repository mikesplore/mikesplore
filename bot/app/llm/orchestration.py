import json
import base64

from groq import APIStatusError

from ..config import settings
from ..tools import TOOLS, execute_tool
from ..admin import get_cv_tailoring_context, list_admin_resource, list_profile_links, search_admin_content, sync_devto_articles
from .client import client, client_answer_kwargs
from .prompts import SYSTEM, EXTRACT_SYSTEM, CV_TAILOR_SYSTEM
from .admin_tools import ADMIN_TOOLS, execute_admin_tool
from .public_tools import answer, present_admin_result

async def extract_entry(instruction: str) -> dict:
    completion = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": instruction}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(completion.choices[0].message.content or "{}")


async def extract_update(instruction: str) -> dict:
    completion = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": "Extract only fields the admin explicitly asks to change. Return JSON using fields title, blurb, date, year, is_visible, is_featured, custom_order, tech_stack, tags, details, links, and media. Return an empty JSON object if unclear."}, {"role": "user", "content": instruction}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(completion.choices[0].message.content or "{}")


async def extract_profile_update(instruction: str) -> dict:
    completion = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": "Extract only profile fields explicitly requested by the admin. Return JSON using name, tagline, location, focus, experience, availability_status, availability_detail, and about."}, {"role": "user", "content": instruction}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(completion.choices[0].message.content or "{}")
    # Profile updates are patch-style. Null fields from JSON mode mean
    # "unspecified", not "clear this existing value".
    return {key: value for key, value in result.items() if value is not None}


async def tailor_cv(job_description: str, existing_patch: dict | None = None, revision: str | None = None) -> dict:
    context = await get_cv_tailoring_context()
    instruction = "JOB DESCRIPTION:\n" + job_description
    instruction += "\n\nVERIFIED BASE CV CONTEXT:\n" + json.dumps(context)
    if existing_patch:
        instruction += "\n\nPENDING PATCH:\n" + json.dumps(existing_patch) + "\n\nREVISION REQUEST:\n" + (revision or "")
    messages = [{"role": "system", "content": CV_TAILOR_SYSTEM}, {"role": "user", "content": instruction}]
    for attempt in range(2):
        try:
            completion = await client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=700,
                temperature=0,
            )
        except APIStatusError as error:
            raise ValueError(groq_error_message(error)) from error
        message = completion.choices[0].message
        if not message.tool_calls:
            content = (message.content or "").strip()
            try:
                if content.startswith("```"):
                    content = content.removeprefix("```").removeprefix("json").removesuffix("```").strip()
                result = json.loads(content or "{}")
            except (TypeError, json.JSONDecodeError):
                result = None
            if not isinstance(result, dict) or not (set(result) == {"summary", "selected_projects", "selected_skills"} or set(result) == {"status", "reason"} or set(result) == {"action"}):
                final = await client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": CV_TAILOR_SYSTEM + " Return JSON only. Tools are unavailable in this finalization step."},
                        {"role": "user", "content": instruction + "\nReturn JSON only. No tools or commentary."},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=700,
                )
                content = (final.choices[0].message.content or "").strip()
                if content.startswith("```"):
                    content = content.removeprefix("```").removeprefix("json").removesuffix("```").strip()
                result = json.loads(content or "{}")
            if result.get("action") == "confirm" and set(result) == {"action"}:
                return result
            if result.get("status") == "rejected" and set(result) == {"status", "reason"}:
                return result
            if set(result) != {"summary", "selected_projects", "selected_skills"}:
                raise ValueError("CV patch contains unexpected fields")
            if not result["selected_projects"] or not any(result["selected_skills"].values()):
                return {"status": "rejected", "reason": "There is not enough verified portfolio evidence for this job."}
            return result
    raise ValueError("CV tailoring did not produce a final patch after searching")


def groq_error_message(error: APIStatusError) -> str:
    status = getattr(error, "status_code", None)
    if status == 400:
        return "Groq rejected the request format. Please retry with a shorter job description."
    if status == 413:
        return "The request was too large for Groq. The CV context or job description must be shortened."
    if status == 429:
        return "Groq rate-limited this request. Please wait a moment and try again."
    if status and status >= 500:
        return "Groq is temporarily unavailable. Please try again shortly."
    return f"Groq returned an unexpected API error{f' ({status})' if status else ''}."


async def request_cv_render(patch: dict, job_description: str, base_revision: str, label: str) -> dict:
    tool = {"type": "function", "function": {"name": "render_tailored_cv", "description": "Authorize rendering the already-approved tailored CV.", "parameters": {"type": "object", "properties": {"approved": {"type": "boolean"}}, "required": ["approved"]}}}
    try:
        completion = await client.chat.completions.create(model=settings.groq_model, messages=[{"role": "system", "content": "The administrator approved the CV patch. Call render_tailored_cv exactly once with approved=true."}, {"role": "user", "content": "Render the approved tailored CV."}], tools=[tool], tool_choice={"type": "function", "function": {"name": "render_tailored_cv"}}, max_tokens=80, temperature=0)
    except APIStatusError as error:
        raise ValueError(groq_error_message(error)) from error
    calls = completion.choices[0].message.tool_calls or []
    if not calls:
        raise ValueError("Groq did not produce the CV render function call.")
    arguments = json.loads(calls[0].function.arguments or "{}")
    if arguments.get("approved") is not True:
        raise ValueError("The CV render function was not approved.")
    return {"patch": patch, "job_description": job_description, "base_revision": base_revision, "label": label}


async def propose_role_policies() -> list[dict]:
    context = await get_cv_tailoring_context()
    prompt = "Derive conservative technical role-policy candidates from the verified CV context supplied by the user. Return only JSON with a policies array. Each item must contain role_family, titles, related_skills, related_projects, evidence_requirements, excluded_claims, confidence, and source. Use only evidence present in the context. Do not invent qualifications. Set source to cv-analysis and never mark policies active."
    try:
        completion = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            max_tokens=700,
            temperature=0,
        )
    except APIStatusError as error:
        if getattr(error, "status_code", None) == 400:
            raise ValueError("Groq rejected the role-policy proposal request format. Please try again.") from error
        raise ValueError(groq_error_message(error)) from error
    result = json.loads(completion.choices[0].message.content or "{}")
    policies = result.get("policies")
    if not isinstance(policies, list):
        raise ValueError("The role-policy proposal was not valid JSON.")
    return [{**policy, "status": "pending", "is_active": False} for policy in policies if isinstance(policy, dict) and policy.get("role_family")]


async def extract_job_description_from_image(content: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(content).decode("ascii")
    completion = await client.chat.completions.create(
        model=settings.groq_vision_model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Extract the complete job description text from this poster. Return only JSON: {\"job_description\": \"...\"}. Do not summarize, invent, or add commentary."},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
        ]}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(completion.choices[0].message.content or "{}")
    text = result.get("job_description")
    if not isinstance(text, str) or len(text.strip()) < 30:
        raise ValueError("The poster did not contain enough readable job description text")
    return text.strip()




async def extract_admin_operation(instruction: str, admin_authorized: bool = False) -> dict:
    allowed_resources = {"entries", "certificates", "assets", "links", "skills", "education", "bucket-list", "settings", "profile", "entry-assets", "entry-technologies", "repositories", "technologies", "topology", "metrics", "decisions", "highlights", "quotes", "snippets", "documents", "badges", "uploads", "cv-tailoring", "role-policies", "devto-sync"}
    system = "Extract one admin portfolio operation as JSON with resource, action (list/create/update/delete), id, and payload. For a read request such as 'list my assets', call the relevant lookup tool, then call create_admin_operation with action=list and payload {}. Never copy lookup records into the payload. For 'activate them' or similar role-policy requests, call list_role_policies, then return resource role-policies, action update, and payload.policies containing each exact policy id with is_active true and status active. Use role-policies updates only after listing exact policies. Do not return a conversational answer. To derive dynamic role policies from the verified CV, call propose_role_policies; it returns resource role-policies and action propose. Use lookup tools before updating or deleting an existing record; copy exact returned IDs and never invent them. Project metadata requests such as changing a project's status or category are entries updates: call list_projects first, select the exact matching project ID, use resource entries and action update, and put only the requested fields in payload. Do not use resource project. Repository metadata requests such as changing a repository's visibility, primary language, label, role, or primary flag are repositories updates: call list_repositories or find_repository first, select the exact matching repository ID, use resource repositories and action update, and put only the requested fields in payload. Map 'show/hide' to is_visible true/false. For any repository URL request, call find_repository with the exact URL first; if it returns a record, action MUST be update with that record's exact ID and never create a duplicate URL. Only use create when find_repository returns no record. To add technologies or any content block to a project, ALWAYS call list_projects first and copy the exact project entry ID into entry_id. For technologies also call list_technologies and use resource entry-technologies. Never use topology for technology relationships. For attaching an asset, call list_assets and list_projects, then create resource entry-assets with payload containing the exact asset_id, entry_id, role, alt_text, caption, and custom_order. Use profile only for profile text. Contact details use links. When one request names multiple contact/social platforms or usernames, create one bulk links operation with payload.links containing one complete link object per named platform; never collapse them into one link. For bulk link updates or deletes, call list_profile_links first and include the exact id in each link object. Infer categories per platform only when the user does not specify one: WhatsApp and Telegram are contact, while dev.to and LabLab AI are social. If the user explicitly says professional, social, or contact, apply that exact category to every named link unless the request assigns categories individually. Project content uses topology, metrics, decisions, highlights, quotes, snippets, documents, or badges with entry_id. Repository metadata uses repositories. Return action null only when a mutation target is genuinely ambiguous."
    async def extract(system_prompt: str, user_prompt: str) -> dict:
        completion = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(completion.choices[0].message.content or "{}")

    explicit_sync = any(word in instruction.lower() for word in ("sync", "import", "refresh", "fetch", "update my dev.to"))
    extraction_tools = [tool for tool in ADMIN_TOOLS if tool["function"]["name"] != "sync_devto_articles" or explicit_sync]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": instruction}]
    for _ in range(3):
        completion = await client.chat.completions.create(model=settings.groq_model, messages=messages, tools=extraction_tools, tool_choice="auto", max_tokens=300, temperature=0)
        message = completion.choices[0].message
        if not message.tool_calls:
            try:
                result = json.loads(message.content or "{}")
                break
            except json.JSONDecodeError as error:
                raise ValueError("The LLM returned an incomplete admin operation") from error
        messages.append(message)
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            if call.function.name in {"create_admin_operation", "request_upload", "request_cv_tailoring", "propose_role_policies", "sync_devto_articles"}:
                if call.function.name == "request_upload":
                    result = {"resource": "uploads", "action": "request", "payload": arguments}
                elif call.function.name == "request_cv_tailoring":
                    result = {"resource": "cv-tailoring", "action": "request", "payload": arguments}
                elif call.function.name == "propose_role_policies":
                    result = await execute_admin_tool(call.function.name, arguments, admin_authorized)
                elif call.function.name == "sync_devto_articles":
                    result = await execute_admin_tool(call.function.name, arguments, admin_authorized)
                else:
                    result = arguments
                break
            tool_result = await execute_admin_tool(call.function.name, arguments, admin_authorized)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(tool_result)})
        else:
            continue
        break
    else:
        raise ValueError("Admin lookup did not produce an operation")
    if not result.get("action") and instruction.lower().lstrip().startswith(("list ", "show ")):
        messages.append({"role": "user", "content": "Return the final operation now. This is a read-only list request. Call create_admin_operation with the correct resource, action=list, and payload={}."})
        completion = await client.chat.completions.create(model=settings.groq_model, messages=messages, tools=ADMIN_TOOLS, tool_choice={"type": "function", "function": {"name": "create_admin_operation"}}, max_tokens=120, temperature=0)
        forced = completion.choices[0].message
        if forced.tool_calls:
            result = json.loads(forced.tool_calls[0].function.arguments or "{}")
    elif not result.get("action"):
        messages.append({"role": "user", "content": "Return the final structured admin operation now. Use the exact record ID from the lookup result, choose the correct resource and action, and call create_admin_operation. Do not perform another lookup."})
        completion = await client.chat.completions.create(model=settings.groq_model, messages=messages, tools=ADMIN_TOOLS, tool_choice={"type": "function", "function": {"name": "create_admin_operation"}}, max_tokens=180, temperature=0)
        forced = completion.choices[0].message
        if forced.tool_calls:
            result = json.loads(forced.tool_calls[0].function.arguments or "{}")
    if not result.get("action") and result.get("resource") and instruction.lower().lstrip().startswith(("list ", "show ")):
        result["action"] = "list"
        result["payload"] = result.get("payload") if isinstance(result.get("payload"), dict) else {}
    if result.get("action") is not None and (result.get("resource") not in allowed_resources or result.get("action") not in {"list", "create", "update", "delete", "request", "propose"}):
        raise ValueError("Unsupported admin operation")
    bulk_link_mutation = (
        result.get("resource") == "links"
        and isinstance(result.get("payload"), dict)
        and isinstance(result["payload"].get("links"), list)
        and all(isinstance(link, dict) and link.get("id") for link in result["payload"]["links"])
    )
    bulk_policy_mutation = (
        result.get("resource") == "role-policies"
        and isinstance(result.get("payload"), dict)
        and isinstance(result["payload"].get("policies"), list)
        and all(isinstance(policy, dict) and policy.get("id") for policy in result["payload"]["policies"])
    )
    if result.get("action") in {"update", "delete"} and result.get("resource") != "profile" and not result.get("id") and not bulk_link_mutation and not bulk_policy_mutation:
        raise ValueError("Admin updates and deletes require an exact record id from a lookup tool")
    if result.get("action") in {"create", "update"} and not isinstance(result.get("payload"), dict):
        raise ValueError("Admin mutations require an object payload")
    if result.get("resource") == "links" and result.get("action") == "create":
        links = (result.get("payload") or {}).get("links") if isinstance(result.get("payload"), dict) else None
        if links is not None and (not isinstance(links, list) or not all(isinstance(link, dict) and link.get("name") and link.get("url") for link in links)):
            raise ValueError("Contact link operation must contain valid links")
    return result

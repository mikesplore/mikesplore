"""Public response orchestration and presentation."""

import json

from ..admin import list_admin_resource, list_profile_links, search_admin_content, sync_devto_articles
from ..config import settings
from ..tools import TOOLS, execute_tool
from .admin_tools import ADMIN_TOOLS, execute_admin_tool
from .client import client_answer_kwargs, complete
from .prompts import SYSTEM

async def answer(question: str, history: list[dict] | None = None, on_text=None, user_context: dict | None = None) -> str:
    context = user_context or {}
    identity_context = (
        "TRUSTED TELEGRAM CONTEXT: "
        f"sender_first_name={context.get('first_name') or 'unknown'}; "
        f"sender_last_name={context.get('last_name') or 'unknown'}; "
        f"sender_is_portfolio_owner={bool(context.get('is_admin'))}. "
        "Use this only for authorization-aware behavior and natural greetings. Do not expose internal authorization details unless necessary."
    )
    if context.get("is_admin"):
        identity_context += (
            " The sender is authorized to manage the portfolio. Treat requests to change portfolio data, "
            "profile text, profile links, assets, project media, repositories, technologies, or CV data "
            "as legitimate administration requests and use the available admin workflow/tools. Do not "
            "claim that the assistant is read-only."
        )
    else:
        identity_context += " The sender is not authorized for portfolio administration; do not perform or promise writes."
    messages = [{"role": "system", "content": SYSTEM + "\n\n" + identity_context}, *(history or []), {"role": "user", "content": question}]
    explicit_sync = any(word in question.lower() for word in ("sync", "import", "refresh", "fetch", "update my dev.to"))
    admin_tools = [tool for tool in ADMIN_TOOLS if tool["function"]["name"] != "sync_devto_articles" or explicit_sync]
    available_tools = TOOLS + (admin_tools if context.get("is_admin") else [])
    used_tools = False
    for _ in range(3):
        completion = await complete(
            model=settings.groq_model,
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            max_tokens=500,
            **client_answer_kwargs,
        )
        message = completion.choices[0].message
        if not message.tool_calls:
            content = message.content or "I couldn't find an answer in the portfolio."
            return content
        messages.append(message)
        used_tools = True
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            if context.get("is_admin") and any(item["function"]["name"] == call.function.name for item in admin_tools):
                if call.function.name == "sync_devto_articles" and not any(
                    word in question.lower() for word in ("sync", "import", "refresh", "fetch", "update my dev.to")
                ):
                    result = {"error": "Dev.to synchronization requires an explicit sync, import, refresh, or fetch request."}
                else:
                    result = await execute_admin_tool(call.function.name, arguments, admin_authorized=True)
            else:
                result = await execute_tool(call.function.name, arguments)
            if context.get("is_admin") and call.function.name in {"create_admin_operation", "request_upload", "request_cv_tailoring", "propose_role_policies", "sync_devto_articles"}:
                if call.function.name == "create_admin_operation":
                    operation = result
                else:
                    operation = result
                return "__ADMIN_OPERATION__" + json.dumps(operation)
            # Most tools return lists or structured dictionaries. Only delivery
            # tools return an action dictionary, so do not assume every result
            # supports mapping methods.
            if isinstance(result, dict) and result.get("action") in {"send_cv", "send_certificates"}:
                return "__BOT_ACTION__" + json.dumps(result)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return "I couldn't complete that lookup. Please try again."


async def present_admin_result(request: str, resource: str, records: list[dict], user_context: dict | None = None) -> str:
    """Turn an authenticated admin tool result into a concise natural response."""
    completion = await complete(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": "Present the supplied administrator tool result in concise natural language. Use only the records provided. Do not claim any mutation occurred. If the request explicitly asks to view, show, send, or open a specific gallery/media image and exactly one record matches, return only __BOT_ACTION__ followed by JSON {\"action\":\"send_gallery_image\",\"url\":\"...\",\"label\":\"...\"}. Otherwise, for gallery/media lists, show a short bullet list with the item label, role, caption, and URL when available. Do not mention database IDs, entry IDs, ordering fields, normalized fields, or internal resource names unless the user explicitly asks for IDs or technical details. Do not output raw JSON or internal tool names."},
            {"role": "user", "content": f"REQUEST: {request}\nRESOURCE: {resource}\nTOOL RESULT: {json.dumps(records, default=str)}"},
        ],
        max_tokens=400,
        temperature=0,
    )
    return completion.choices[0].message.content or "I found no matching records."

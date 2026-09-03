import json

from groq import AsyncGroq

from .config import settings
from .tools import TOOLS, execute_tool

client = AsyncGroq(api_key=settings.groq_api_key)
SYSTEM = "You answer questions about Michael Odhiambo's portfolio. Use search_portfolio first for broad or ambiguous questions; it searches the profile and all public content. Use get_profile for direct identity/background questions and list_entries for filtered lists. Use tools for every factual claim about Mike. Always state the total number of matching records when listing results. If more records exist than the current page, present the page and ask whether the user wants more. When the user asks for more, request the next page. If the tools have no supporting data, say you do not know. Be concise and format answers with Telegram Markdown."
EXTRACT_SYSTEM = "Extract one portfolio entry from the admin instruction. Return only JSON with slug, content_type (project/article/hackathon/event), title, blurb, date (YYYY-MM-DD or null), year, is_visible, is_featured, custom_order, tech_stack, tags, details, links, media, and source. Infer nothing not present; use null or empty values."


async def answer(question: str) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(3):
        completion = await client.chat.completions.create(model=settings.groq_model, messages=messages, tools=TOOLS, tool_choice="auto")
        message = completion.choices[0].message
        if not message.tool_calls:
            return message.content or "I couldn't find an answer in the portfolio."
        messages.append(message)
        for call in message.tool_calls:
            result = await execute_tool(call.function.name, json.loads(call.function.arguments or "{}"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return "I couldn't complete that lookup. Please try again."


async def extract_entry(instruction: str) -> dict:
    completion = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": instruction}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(completion.choices[0].message.content or "{}")


async def extract_update(instruction: str) -> dict:
    completion = await client.chat.completions.create(model=settings.groq_model, messages=[{"role": "system", "content": "Extract only fields the admin explicitly asks to change. Return JSON using fields title, blurb, date, year, is_visible, is_featured, custom_order, tech_stack, tags, details, links, and media. Return an empty JSON object if unclear."}, {"role": "user", "content": instruction}], response_format={"type": "json_object"}, temperature=0)
    return json.loads(completion.choices[0].message.content or "{}")


async def extract_profile_update(instruction: str) -> dict:
    completion = await client.chat.completions.create(model=settings.groq_model, messages=[{"role": "system", "content": "Extract only profile fields explicitly requested by the admin. Return JSON using name, tagline, location, focus, experience, availability_status, availability_detail, and about."}, {"role": "user", "content": instruction}], response_format={"type": "json_object"}, temperature=0)
    return json.loads(completion.choices[0].message.content or "{}")


async def extract_admin_operation(instruction: str) -> dict:
    system = "Extract one admin portfolio CRUD operation. Return only JSON with resource (entries, certificates, assets, links, skills, education, bucket-list, settings, profile), action (create, update, delete), id (string or null), and payload (object). Never invent IDs or values. Use profile for profile field updates."
    completion = await client.chat.completions.create(model=settings.groq_model, messages=[{"role": "system", "content": system}, {"role": "user", "content": instruction}], response_format={"type": "json_object"}, temperature=0)
    result = json.loads(completion.choices[0].message.content or "{}")
    if result.get("resource") not in {"entries", "certificates", "assets", "links", "skills", "education", "bucket-list", "settings", "profile"} or result.get("action") not in {"create", "update", "delete"}:
        raise ValueError("Unsupported admin operation")
    return result

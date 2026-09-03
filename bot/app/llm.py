import json

from groq import AsyncGroq

from .config import settings
from .tools import TOOLS, execute_tool

client = AsyncGroq(api_key=settings.groq_api_key)
SYSTEM = "You answer questions about Michael Odhiambo's portfolio. Use the portfolio tool for every factual claim about Mike. If the tool has no supporting data, say you do not know. Be concise."
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

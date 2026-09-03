import json

from groq import AsyncGroq

from .config import settings
from .tools import TOOLS, execute_tool

client = AsyncGroq(api_key=settings.groq_api_key)
SYSTEM = "You answer questions about Michael Odhiambo's portfolio. Use the portfolio tool for every factual claim about Mike. If the tool has no supporting data, say you do not know. Be concise."


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

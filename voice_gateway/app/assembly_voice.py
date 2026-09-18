"""AssemblyAI Voice Agent API bridge for the hackathon runtime."""

import asyncio
import base64
import json
import logging
import time

import httpx
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError

from .config import settings
from .tools import TOOLS, execute_tool

logger = logging.getLogger("uvicorn.error")

ASSEMBLY_AGENT_URL = "wss://agents.assemblyai.com/v1/ws"


async def validate_owner_session(token: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(base_url=settings.backend_url, timeout=5) as client:
            response = await client.get("/owner/status", headers={"Authorization": f"Bearer {token}"})
        return response.is_success
    except httpx.HTTPError:
        logger.warning("owner session validation failed through main backend")
        return False


def assembly_tools() -> list[dict]:
    """Convert the existing OpenAI-shaped public tools to AssemblyAI's flat schema."""
    converted = []
    delivery_tools = {"request_cv_delivery", "request_certificate_delivery"}
    for item in TOOLS:
        function = item["function"]
        if function["name"] in delivery_tools:
            continue
        converted.append({
            "type": "function",
            "name": function["name"],
            "description": function.get("description", ""),
            "parameters": function.get("parameters", {"type": "object", "properties": {}}),
        })
    return converted


SYSTEM_PROMPT = (
    "You are the spoken interface for Mike's portfolio. Use the provided verified tools for "
    "portfolio facts and never invent information. Keep spoken replies concise, natural, and "
    "under three short sentences. You may use tools to look up public projects, articles, skills, "
    "contact links, CV information, certificates, and public media. For a requested public file "
    "or image, use the public-media tool so the browser can display a verified card. For a named certificate, use list_certificates with its title as the query. If the visitor asks to end, stop, or close the conversation, acknowledge it briefly and do not call another tool. Never perform "
    "mutations or claim an upload occurred. Distinguish read requests from mutations: show, view, display, open, list, find, or download are public read requests and must never request owner unlock. Treat only explicit mutation verbs such as upload, update, replace, change, edit, delete, curate, or set as owner mutations, even when the user says profile picture, profile photo, CV, certificate, project, link, or skill. For any such request, call request_owner_unlock first and wait for the browser PIN flow. Do not answer that the action is done before the browser confirms it."
)


async def send_verified_actions(websocket: WebSocket, tool_name: str, result) -> list[dict]:
    """Turn trusted tool URLs into explicit browser cards/buttons."""
    items = []
    if tool_name == "list_public_assets" and isinstance(result, list):
        items = [{"type": "display_item", "item_type": item.get("type", "media"), "label": item.get("label") or "Public media", "url": item.get("url")} for item in result]
    elif tool_name == "list_certificates" and isinstance(result, list):
        items = [{"type": "display_item", "item_type": "certificate", "label": item.get("title") or "Certificate", "url": item.get("image_url")} for item in result]
    elif tool_name == "get_entry_by_slug" and isinstance(result, dict) and result.get("found"):
        items = [{"type": "open_resource", "item_type": result.get("content_type", "resource"), "label": result.get("title") or "Open resource", "url": result.get("url")}]
    elif tool_name in {"list_entries", "list_articles", "search_articles", "search_portfolio"} and isinstance(result, dict):
        records = result.get("entries", result.get("articles", []))
        items = [{"type": "open_resource", "item_type": item.get("content_type", "resource"), "label": item.get("title") or "Open resource", "url": item.get("url")} for item in records]
    safe_items = [item for item in items if isinstance(item.get("url"), str) and item["url"].startswith("https://")]
    logger.info("verified browser actions tool=%s candidates=%d emitted=%d", tool_name, len(items), len(safe_items[:5]))
    return safe_items[:5]


async def voice_agent_websocket(websocket: WebSocket) -> None:
    try:
        import websockets
    except ImportError:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Voice dependencies are not installed."})
        await websocket.close(code=1011)
        return

    await websocket.accept()
    logger.info("voice client connected")

    async def send_client(payload: dict) -> bool:
        """Send to the browser without masking an already-closed client."""
        try:
            await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            logger.info("voice client disconnected while sending event=%s", payload.get("type"))
            return False

    if not settings.assemblyai_api_key:
        await send_client({"type": "error", "message": "AssemblyAI is not configured yet."})
        await websocket.close(code=1011)
        return

    headers = {"Authorization": f"Bearer {settings.assemblyai_api_key}"}
    try:
        logger.info("opening AssemblyAI Voice Agent connection url=%s", ASSEMBLY_AGENT_URL)
        async with websockets.connect(
            ASSEMBLY_AGENT_URL,
            additional_headers=headers,
            max_size=None,
            open_timeout=15,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ) as agent:
            agent_ready = asyncio.Event()
            audio_bytes = 0
            audio_frames = 0
            last_audio_log = time.monotonic()
            pending_browser_actions = []
            owner_unlocked = False
            pending_owner_action = ""
            logger.info("assemblyai voice session connecting")
            await agent.send(json.dumps({
                "type": "session.update",
                "session": {
                    "system_prompt": SYSTEM_PROMPT,
                    "input": {
                        "format": {"encoding": "audio/pcm"},
                        "transcription_mode": "max_accuracy",
                        "transcription_prompt": "This is a portfolio conversation about software projects, programming, APIs, databases, cloud services, and web development. Preserve technical terms accurately.",
                        "voice_focus": "near-field",
                        "voice_focus_threshold": 0.8,
                        "turn_detection": {"interrupt_response": True, "vad_threshold": 0.35, "min_silence": 500, "max_silence": 2500},
                    },
                    "output": {"voice": "emma", "format": {"encoding": "audio/pcm"}, "volume": 100},
                    "tools": assembly_tools(),
                },
            }))

            async def forward_client() -> None:
                nonlocal audio_bytes, audio_frames, last_audio_log, owner_unlocked
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        return
                    if message.get("bytes"):
                        await agent_ready.wait()
                        audio_bytes += len(message["bytes"])
                        audio_frames += 1
                        if time.monotonic() - last_audio_log >= 2:
                            logger.info("voice audio received frames=%d bytes=%d", audio_frames, audio_bytes)
                            last_audio_log = time.monotonic()
                        await agent.send(json.dumps({"type": "input.audio", "audio": base64.b64encode(message["bytes"]).decode()}))
                    elif message.get("text"):
                        command = json.loads(message["text"])
                        if command.get("type") == "stop":
                            await agent.send(json.dumps({"type": "session.end"}))
                            return
                        if command.get("type") == "owner_session":
                            owner_unlocked = await validate_owner_session(command.get("token", ""))
                            logger.info("owner session forwarded valid=%s", owner_unlocked)
                            await send_client({"type": "owner_unlocked" if owner_unlocked else "owner_locked"})
                            if owner_unlocked and "profile" in pending_owner_action.lower() and ("picture" in pending_owner_action.lower() or "photo" in pending_owner_action.lower()):
                                await send_client({"type": "upload_requested", "action": pending_owner_action})

            client_task = asyncio.create_task(forward_client())
            try:
                async for raw in agent:
                    if isinstance(raw, bytes):
                        continue
                    event = json.loads(raw)
                    event_type = event.get("type")
                    if event_type == "session.ready":
                        agent_ready.set()
                        logger.info("assemblyai session ready")
                        await send_client({"type": "ready", "sample_rate": 24000, "provider": "assemblyai-voice-agent"})
                    elif event_type == "reply.audio":
                        if pending_browser_actions:
                            await send_client({"type": "actions", "items": pending_browser_actions})
                            pending_browser_actions.clear()
                        audio = event.get("data", "")
                        logger.debug("assemblyai audio response chunk base64_bytes=%d", len(audio))
                        await send_client({"type": "audio", "audio": audio})
                    elif event_type in {"transcript.user", "transcript.user.delta"}:
                        text = event.get("text") or event.get("transcript") or ""
                        if text:
                            logger.info("voice transcript event final=%s text=%r", event_type == "transcript.user", text[:160])
                            await send_client({"type": "transcript", "text": text, "final": event_type == "transcript.user"})
                    elif event_type == "transcript.agent":
                        text = event.get("text") or ""
                        if text:
                            await send_client({"type": "response", "text": text})
                    elif event_type == "tool.call":
                        call_id = event.get("call_id") or event.get("id")
                        name = event.get("name") or event.get("function", {}).get("name")
                        arguments = event.get("arguments") or event.get("function", {}).get("arguments") or {}
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments or "{}")
                        logger.info("voice tool call name=%s call_id=%s", name, call_id)
                        try:
                            result = await execute_tool(name, arguments)
                        except Exception as error:
                            logger.exception("voice tool failed name=%s", name)
                            result = {"error": "The verified portfolio lookup failed."}
                        logger.info("voice tool result name=%s success=%s", name, "error" not in result if isinstance(result, dict) else True)
                        await agent.send(json.dumps({
                            "type": "tool.result",
                            "call_id": call_id,
                            "result": json.dumps(result, default=str),
                            "is_error": isinstance(result, dict) and "error" in result,
                        }))
                        if name == "request_owner_unlock" and isinstance(result, dict) and result.get("action") == "request_owner_unlock":
                            action = result.get("requested_action", "owner action")
                            pending_owner_action = action
                            if owner_unlocked:
                                await send_client({"type": "upload_requested" if "profile" in action.lower() and ("picture" in action.lower() or "photo" in action.lower()) else "owner_unlocked", "action": action})
                            else:
                                await send_client({"type": "pin_required", "title": "Enter your PIN to continue", "action": action})
                        pending_browser_actions.extend(await send_verified_actions(websocket, name, result))
                    elif event_type in {"reply.done", "input.speech.started"}:
                        logger.info("assemblyai event=%s status=%s", event_type, event.get("status"))
                        await send_client({"type": "interrupted" if event.get("status") == "interrupted" else "listening" if event_type == "input.speech.started" else "reply_done"})
                    elif event_type == "session.error":
                        logger.error("assemblyai session error details=%s", event)
                        await send_client({"type": "error", "message": "AssemblyAI voice session failed."})
            finally:
                client_task.cancel()
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except ConnectionClosedError as error:
        logger.info("voice session ended while closing upstream AssemblyAI connection: %s", error)
        return
    except TimeoutError:
        logger.info("voice session close timed out after the browser disconnected")
        return
    except Exception:
        logger.exception("voice session failed")
        await send_client({"type": "error", "message": "AssemblyAI voice session failed."})

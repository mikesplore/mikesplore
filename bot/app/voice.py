"""Phase 1 browser voice loop.

The browser sends 16 kHz, mono, signed 16-bit PCM frames. This module forwards
those frames to AssemblyAI, turns completed transcripts into a plain Groq
response, and streams an ElevenLabs MP3 response back to the browser.
"""

import asyncio
import base64
import json
from urllib.parse import urlencode

import httpx
from fastapi import WebSocket, WebSocketDisconnect

from .config import settings
from .llm.client import complete


ASSEMBLYAI_URL = "wss://streaming.assemblyai.com/v3/ws"
VOICE_SYSTEM = (
    "You are the spoken interface for Mike's portfolio. Answer briefly and naturally. "
    "This is phase one, so do not claim to have searched portfolio data or performed actions. "
    "Say that portfolio-connected capabilities are being added if asked."
)


def assemblyai_url() -> str:
    return ASSEMBLYAI_URL + "?" + urlencode({
        "sample_rate": 16000,
        "format_turns": True,
        "speech_model": "universal-streaming-english",
    })


async def _answer(transcript: str) -> str:
    completion = await complete(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": VOICE_SYSTEM},
            {"role": "user", "content": transcript},
        ],
        max_tokens=180,
        temperature=0,
        _usage_workflow="voice_phase1",
    )
    return completion.choices[0].message.content or "I couldn't form a response."


async def _send_tts(websocket: WebSocket, text: str) -> None:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        await websocket.send_json({"type": "error", "message": "TTS is not configured yet."})
        return
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}/stream"
    params = {"output_format": "mp3_22050_32"}
    payload = {"text": text, "model_id": settings.elevenlabs_model}
    headers = {"xi-api-key": settings.elevenlabs_api_key, "accept": "audio/mpeg"}
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream("POST", url, params=params, json=payload, headers=headers) as response:
            response.raise_for_status()
            await websocket.send_json({"type": "speech_started", "text": text})
            async for chunk in response.aiter_bytes():
                if chunk:
                    await websocket.send_json({"type": "audio", "data": base64.b64encode(chunk).decode("ascii")})
    await websocket.send_json({"type": "speech_finished"})


async def voice_websocket(websocket: WebSocket) -> None:
    try:
        import websockets
    except ImportError:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Voice dependencies are not installed."})
        await websocket.close(code=1011)
        return
    await websocket.accept()
    if not settings.assemblyai_api_key:
        await websocket.send_json({"type": "error", "message": "AssemblyAI is not configured yet."})
        await websocket.close(code=1011)
        return

    response_task: asyncio.Task | None = None
    try:
        headers = {"Authorization": settings.assemblyai_api_key}
        async with websockets.connect(assemblyai_url(), additional_headers=headers, max_size=None) as assembly:
            await websocket.send_json({"type": "ready", "sample_rate": 16000})

            async def forward_audio() -> None:
                while True:
                    message = await websocket.receive()
                    if message.get("type") == "websocket.disconnect":
                        return
                    if message.get("bytes"):
                        await assembly.send(message["bytes"])
                    elif message.get("text"):
                        command = json.loads(message["text"])
                        if command.get("type") == "stop":
                            await assembly.send(json.dumps({"type": "Terminate"}))
                            return
                        if command.get("type") == "interrupt" and response_task and not response_task.done():
                            response_task.cancel()

            forward_task = asyncio.create_task(forward_audio())
            try:
                async for raw in assembly:
                    if isinstance(raw, bytes):
                        continue
                    event = json.loads(raw)
                    event_type = event.get("type")
                    if event_type == "Begin":
                        await websocket.send_json({"type": "transcription_started"})
                    elif event_type == "SpeechStarted":
                        await websocket.send_json({"type": "listening"})
                    elif event_type == "Turn":
                        transcript = (event.get("transcript") or "").strip()
                        await websocket.send_json({"type": "transcript", "text": transcript, "final": bool(event.get("end_of_turn"))})
                        if transcript and event.get("end_of_turn") and event.get("turn_is_formatted"):
                            if response_task and not response_task.done():
                                response_task.cancel()
                            await websocket.send_json({"type": "thinking"})
                            response_task = asyncio.create_task(_answer(transcript))
                            try:
                                answer = await response_task
                                await websocket.send_json({"type": "response", "text": answer})
                                await _send_tts(websocket, answer)
                            except asyncio.CancelledError:
                                await websocket.send_json({"type": "interrupted"})
                    elif event_type == "Error":
                        await websocket.send_json({"type": "error", "message": event.get("error", "AssemblyAI error")})
            finally:
                forward_task.cancel()
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception as error:
        await websocket.send_json({"type": "error", "message": str(error)})
    finally:
        if response_task and not response_task.done():
            response_task.cancel()

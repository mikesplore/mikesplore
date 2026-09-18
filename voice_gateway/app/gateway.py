"""Standalone AssemblyAI voice gateway for the hackathon deployment."""

from fastapi import FastAPI, WebSocket

from .assembly_voice import voice_agent_websocket

app = FastAPI(title="Milo Voice Gateway", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "voice-gateway"}


@app.websocket("/ws/voice")
@app.websocket("/ws/voice/")
async def voice_socket(websocket: WebSocket):
    await voice_agent_websocket(websocket)

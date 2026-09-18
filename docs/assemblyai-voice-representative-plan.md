# Mikesplore Voice Representative — AssemblyAI Hackathon Plan

## 1. Product concept

Build a voice-first AI representative for Mikesplore. Visitors can speak with an assistant that answers questions about Mike using verified portfolio data. Mike can use a protected owner mode for private, read-only workflows and—if time permits—email drafting with explicit approval before sending.

The hackathon contribution is the voice interaction layer. Mikesplore remains the source of truth for profile, projects, skills, experience, CV, articles, links, and contact options.

## 2. Primary demo

### Visitor mode

1. Visitor opens a dedicated “Talk to Mike” page.
2. Visitor grants microphone access and asks a question naturally.
3. Browser audio travels through the backend WebSocket to AssemblyAI for transcription.
4. The agent uses the shared public tool layer to retrieve verified Mikesplore data.
5. A spoken response is returned, with visible transcript and tool/activity state.
6. Visitor can ask for an appropriate contact path or leave a lead/message.

### Owner mode

1. Mike unlocks the session with a typed PIN/passphrase.
2. Mike asks for a private summary, initially limited to approved read-only tools.
3. If email is implemented, the assistant drafts a reply and displays it for confirmation.
4. Sending is a separate, explicit confirmation action; there is no autonomous sending.

## 3. Architecture

```text
Browser microphone
    ↓ WebSocket
FastAPI voice endpoint (/ws/voice)
    ↓ server-side credentials
AssemblyAI realtime speech-to-text
    ↓ transcript / turn events
Shared agent and tool layer
    ├─ public Mikesplore REST endpoints
    └─ owner-scoped tools after authentication
    ↓ response text
Browser-native speechSynthesis
    ↓ spoken response
Browser playback
```

- The browser never receives AssemblyAI or Groq secrets.
- The Telegram bot and voice agent reuse the same tool contracts and backend REST API.
- The voice endpoint must support cancellation: a new user turn stops playback and cancels the current response where possible.
- Conversation state is scoped to a connection initially; persistent memory is out of scope.

## 4. Technology decisions

- Backend: existing FastAPI service.
- Frontend: existing React/Vite frontend, with a separate voice route/page.
- Speech-to-text: AssemblyAI realtime API.
- Agent: existing Groq integration, initially plain chat and later shared tool calling.
- Speech output: browser-native `speechSynthesis` for Phase 1, avoiding a second paid provider. A hosted TTS provider can be added later if voice quality becomes a submission requirement.
- Transport: WebSocket between browser and FastAPI.
- Authentication: visitor mode is public/read-only; owner mode uses a short-lived session unlocked by a typed PIN/passphrase.

## 5. Scope by phase

### Phase 0 — preparation

- Create an isolated Git branch.
- Inspect the Telegram bot and identify existing public tools, LLM loop, formatting, and backend client code.
- Define a shared tool interface without changing behavior.
- Confirm AssemblyAI credits, API limits, and environment-variable names.
- Check the deployment host’s WebSocket and concurrent-connection limits.

### Phase 1 — prove the voice loop

Browser microphone → FastAPI WebSocket → AssemblyAI transcription → plain Groq response → browser speech synthesis.

Required states: listening, thinking, speaking, error, and disconnected. Validate latency, interruption, cancellation, reconnect behavior, and microphone permissions before adding portfolio data.

### Phase 2 — visitor representative

- Reuse the shared public tool layer.
- Start with `get_profile`, `search_projects`, `get_project`, `get_experience`, and `get_contact_options`.
- Ground responses in returned data and clearly handle missing information.
- Add a safe contact/lead capture flow if it fits the existing backend; otherwise expose the existing contact path.

### Phase 3 — owner mode

- Add typed session unlock and server-side authorization checks.
- Begin with read-only owner tools.
- Ensure visitor connections cannot invoke owner tools, even if they send crafted WebSocket messages.

### Phase 4 — email stretch goal

- Add OAuth and email retrieval only if Phases 1–3 are stable.
- Implement `search_emails`, `get_email`, and `draft_reply` first.
- Add `send_reply` only behind a visible confirmation step.
- Cut email entirely if it threatens the core voice demo.

### Phase 5 — polish and submission

- Improve transcripts, activity indicators, interruption UX, empty/error states, and responsive layout.
- Add a short architecture diagram, setup instructions, demo script, screenshots, and recorded demo.
- Remove or rotate AssemblyAI credentials after the hackathon and document required environment variables.

## 6. Explicit non-goals

Calendar scheduling, autonomous email sending, WhatsApp/CRM integrations, arbitrary web browsing, general-purpose Jarvis behavior, long-term memory, and a full redesign of Mikesplore are excluded from the MVP.

## 7. Acceptance criteria

- A visitor can complete a natural voice question from microphone input to spoken answer.
- The response can use real Mikesplore data without inventing portfolio facts.
- The UI clearly communicates listening, thinking, speaking, and failures.
- Speaking during playback interrupts the current response cleanly.
- Provider credentials remain server-side.
- Public and owner tool permissions are enforced server-side.
- Any email send requires explicit confirmation.
- Existing Mikesplore and Telegram behavior remains functional.
- The project can be run with documented environment variables and can be safely stripped of expiring AssemblyAI credentials afterward.

## 8. Suggested execution order

1. Create branch and audit current integration points.
2. Verify AssemblyAI credit access and browser speech synthesis.
3. Extract or formalize shared tools.
4. Build and test the standalone voice loop.
5. Connect visitor tools.
6. Add owner authentication and read-only tools.
7. Attempt email only if ahead of schedule.
8. Polish, test, document, and prepare the submission.

## 9. Risk controls

- Keep the voice page isolated so it can be removed without affecting the portfolio.
- Use feature flags or route-level isolation for incomplete functionality.
- Never commit API keys; use local environment files excluded by Git.
- Keep AssemblyAI usage bounded during development and reserve credits for end-to-end tests and the final demo.
- Make the final demo work with a small, deterministic tool set rather than depending on every possible integration.

## 10. Phase 0 audit findings — 2026-09-18

- Work is isolated on the `assemblyai-voice-representative` branch.
- The existing public portfolio tool layer is already reusable: `bot/app/tools.py` contains the
  backend REST wrappers, `TOOLS` definitions, and `execute_tool()` dispatcher. The voice agent
  should call this layer rather than duplicate `search_projects`, profile, skills, and contact
  behavior.
- The existing Groq orchestration is Telegram-oriented in `bot/app/llm/public_tools.py`, but the
  lower-level completion wrapper is shared in `bot/app/llm/client.py`. Voice should use a small
  channel-neutral agent adapter around these existing pieces rather than importing Telegram
  handlers.
- The FastAPI backend currently has no voice WebSocket endpoint. The frontend currently has no
  voice route or audio-streaming client.
- The repository now has AssemblyAI configuration and browser-native speech output; no second
  speech provider or API key is required for Phase 1.
- The combined deployment mounts the Telegram app into the backend service, so the new endpoint
  must avoid interfering with existing HTTP routes and Telegram webhook handling.

### Live test readiness

- The code path is ready for a live test, but the local `.env` currently has no
  `ASSEMBLYAI_API_KEY`. The key must be added
  locally or in the deployment environment before opening `/talk` for an end-to-end microphone
  test. Values must remain uncommitted.

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

## 11. Phase 1 completion and Phase 2 start — 2026-09-18

- The live browser and Android microphone flow has been tested successfully through AssemblyAI,
  Groq, and browser speech synthesis.
- The WebSocket 403 was fixed by annotating FastAPI handler parameters as `WebSocket`; the local
  handshake now returns the ready event. Uvicorn is run with `--ws websockets-sansio` for the
  installed `websockets 15.x` runtime.
- Voice responses now reuse `bot/app/llm/public_tools.py`, so visitor questions are grounded in
  the same verified backend REST tools as Telegram. Voice always passes a non-admin context and
  does not expose Telegram file-delivery actions as raw control messages.
- Next work is Phase 2 validation and polish: exercise profile, project, skills, experience, and
  contact questions over the public deployment; then tighten spoken response length, interruption,
  and tool-error handling before adding owner mode.

## 12. Phase 2 completion — 2026-09-18

- Visitor voice questions now reuse the verified public tool layer for profile, projects, articles,
  skills, search, CV search, certificates, and contact links; no visitor path receives admin tools.
- Conversation history is connection-scoped and bounded to the latest three exchanges, enabling
  grounded follow-up questions without persistent visitor memory.
- AssemblyAI speech-start events cancel an in-flight answer, and the browser cancels speech
  synthesis immediately, completing the interruption path.
- Backend/tool failures are converted to a safe retry message rather than exposing provider or
  internal exception details to visitors.
- Phase 2 is complete. Phase 3 (owner mode) is the next phase; email remains deferred.

## 13. Phase 3 owner-mode foundation — 2026-09-18

- Added the optional `VOICE_OWNER_PIN` server-side setting and a WebSocket
  `{"type":"unlock_owner","pin":"..."}` handshake.
- PIN comparison uses constant-time comparison. A successful unlock is scoped to the current
  connection and expires after 15 minutes; failed unlocks return only a generic denial event.
- The initial owner-mode foundation remains read-only and does not expose Telegram admin tools or
  write operations through voice. The frontend unlock control and a dedicated allowlisted owner
  read-only tool set are the next implementation slice.

### Phase 3 completion checklist

- Owner mode now uses an explicit allowlist of verified read-only portfolio tools; delivery tools,
  admin tools, and mutation operations are excluded before the Groq request is made.
- The owner session is connection-scoped, expires after 15 minutes, emits an expiry event, and the
  frontend shows a countdown and requires re-unlock after expiry.
- Invalid unlocks remain generic, and the PIN is checked with constant-time comparison.
- Automated checks cover the tool boundary and session duration. Phase 3 is complete; email and
  other write-capable owner workflows remain intentionally out of scope.

### Planned voice resource actions

- Implemented safe browser actions for visitor requests to view public resources. Voice tool
  results can emit structured `open_resource` actions for verified project, article, and contact
  URLs; the frontend renders explicit click-to-open buttons and never navigates automatically.
- Action generation is limited to HTTPS URLs returned by approved backend tools, capped at five
  actions per response, and never accepts arbitrary URLs generated by the model.
- Keep file delivery separate from voice playback: CV and certificate requests should produce a
  visible, user-triggered link or download control only when the resource is public and available.
- Never expose private files, admin resources, service credentials, raw backend URLs, or arbitrary
  model-generated navigation targets. Validate every action against verified tool output and an
  allowlist of supported URL schemes and portfolio routes.

### Voice action slice verification (2026-09-18)

- Added action collection to the shared public-tool orchestration and forwarded actions through the
  voice WebSocket as a separate `actions` event, preserving the spoken response path.
- Added frontend buttons with a new-tab click requirement and no automatic redirect.
- Added regression coverage proving non-HTTPS URLs are rejected. Bot suite: 50 tests passing;
  Python compilation and `git diff --check` also pass. The frontend production build still needs
  to be run from the host where npm is installed.

### Media upload and production verification (2026-09-18)

- Hardened voice uploads: the backend checks the active owner-session expiry, enforces the 5 MB
  limit, validates profile-image versus PDF MIME types, rejects unsupported action/target pairs,
  and forwards uploads only through the service-key-protected backend endpoint.
- File selection now requires an explicit frontend confirmation before bytes are sent. Successful
  uploads immediately add the refreshed verified asset card to the voice page.
- Bot tests: 50 passing; Python compilation and `git diff --check` pass.
- The frontend build could not be executed in this environment because the host npm executable is
  not available to the agent. Run `npm run build` from `frontend/` on the host.

### AssemblyAI runtime strip started (2026-09-18)

- Added `requirements.hackathon.txt`, containing only the portfolio API, storage, and AssemblyAI
  Voice Agent runtime dependencies; it intentionally excludes Groq and aiogram.
- The active backend route now imports `bot.app.assembly_voice` and no longer mounts the Telegram
  FastAPI application. The old Telegram/Groq files remain as unreferenced migration artifacts
  because this environment's Git index is read-only and cannot safely perform the requested file
  deletion. They must be removed and committed once the repository is writable.
- The new AssemblyAI adapter uses the existing verified REST tool functions directly, registers
  AssemblyAI's flat tool schema, and handles `tool.call`/`tool.result` without the Groq layer.

### Runtime strip completed (2026-09-18)

- Removed the obsolete Telegram application, Groq orchestration, old fallback voice path, and
  their tests from this branch. `main` remains the full Mikesplore product.
- Removed Groq and aiogram from the shared dependency manifest and removed the unused EmailJS
  frontend dependency from the hackathon package manifest.
- Added AssemblyAI-specific adapter tests. The remaining `telegram_user_id` database columns are
  historical schema fields and are not imported by the hackathon runtime.
- For the first submission version, unfinished owner/PIN upload controls were removed from the
  standalone voice UI. The demo is intentionally public read-only: verified portfolio lookups,
  spoken answers, and explicit resource cards. Authenticated media mutation can return in a later
  product branch after the hackathon submission.
- No reverse-proxy or process-manager configuration is committed in this repository. Production
  must route `GET /ws/voice` to the bot/combined ASGI process with HTTP/1.1 upgrade support and
  long-lived WebSocket timeouts. The ASGI process should use `--ws websockets-sansio` (or `--ws
  auto` with a compatible Uvicorn version), bind to the internal service interface, and expose
  `/ws/voice` on the same public origin used by `VITE_API_BASE_URL`.

## Hackathon branch stripping plan — AssemblyAI Voice Agent migration

The `assemblyai-voice-representative` branch will become a focused hackathon build while
`main` remains the complete Mikesplore product. This is a runtime/dependency simplification,
not a history rewrite or an attempt to misrepresent authorship. The submission README will
accurately disclose AssemblyAI, the portfolio backend, and any retained supporting libraries.

### Keep in the hackathon branch

- The standalone `/talk` frontend page and its responsive microphone/audio experience.
- The portfolio backend's public read APIs, database models, media storage, and safe validation.
- Only the voice-specific WebSocket/token boundary needed to connect the browser to AssemblyAI.
- Verified portfolio tools: profile, projects, articles, skills, contact links, public media, and
  explicitly confirmed owner actions.
- AssemblyAI configuration, browser-safe temporary-token support, and AssemblyAI Voice Agent event
  handling for audio input/output, tool calls, interruptions, and session errors.
- Minimal frontend dependencies needed to build the standalone voice demo.

### Remove from the hackathon runtime

- Groq client configuration, model selection, completion wrappers, usage accounting, and voice
  orchestration through `bot/app/llm/*`.
- Telegram/aiogram startup, webhook routes, command handlers, browsing wizard, Telegram delivery,
  and Telegram-specific state.
- `bot/app/main.py` as the combined Telegram application entrypoint, replacing it with a small
  AssemblyAI voice service entrypoint or a backend-owned voice router.
- Groq and aiogram dependencies from the hackathon requirements file.
- Voice-specific browser speech synthesis once AssemblyAI Voice Agent audio playback is working.
- Unused email/contact automation dependencies from the hackathon frontend bundle unless they are
  still needed by a non-voice page included in the submitted demo.

### Migration order and safety gates

1. Create a file/dependency inventory and record the current passing baseline.
2. Add the AssemblyAI Voice Agent adapter beside the current STT adapter; do not delete the
   working path until audio-in/audio-out, tool calls, and interruption are verified.
3. Move the verified portfolio tools to AssemblyAI's flat Voice Agent tool schema and implement
   `tool.call` → backend lookup/action → `tool.result` handling.
4. Add a server-minted temporary AssemblyAI browser token; never expose the permanent API key.
5. Switch the standalone voice page to AssemblyAI audio output and remove browser TTS only after
   the live response and barge-in tests pass.
6. Remove Groq/Telegram runtime code and dependencies from this branch, preserving them on `main`.
7. Run backend tests, voice protocol tests, frontend build, public-domain WebSocket tests, and
   Android tests before committing the stripped branch.

### Acceptance gates before deletion

- AssemblyAI session reaches `session.ready`.
- Microphone PCM reaches AssemblyAI and spoken PCM returns to the browser.
- A portfolio question invokes a verified tool and the spoken answer uses its result.
- A visitor cannot invoke owner-only tools or arbitrary URLs.
- PIN-gated media actions require authorization and explicit confirmation.
- Interruption stops the current AssemblyAI response and playback.
- No `GROQ_*`, Telegram webhook, aiogram startup, or permanent AssemblyAI secret is present in
  the submitted runtime path.

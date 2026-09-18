# Voice Representative Functionality

## Purpose

The `/talk` page is a voice-first interface for browsing Mike's public portfolio and, when explicitly unlocked by Mike, curating private portfolio content. AssemblyAI Voice Agent handles the live voice conversation, while the backend remains the authority for data access, permissions, and writes.

The interface should work for visitors who only want to ask questions and for Mike when he needs to manage portfolio content from the same voice page.

## Public visitor capabilities

Visitors do not need an account, PIN, or separate login.

### Ask questions by voice

Visitors can ask natural questions about:

- Mike's profile, background, location, availability, and experience
- Projects and technical work
- Articles and published writing
- Hackathons and events
- Skills and technologies
- Education
- Certificates
- Bucket-list progress
- Public contact and professional links

The agent answers from verified backend data. It must not invent portfolio facts.

### Browse verified content

The voice agent can return structured browser actions for:

- Project cards
- Article links
- Hackathon and event links
- Profile pictures
- CV documents
- Certificates
- Other approved public media

The frontend displays returned content as grouped sections rather than one flat list. A new final visitor request replaces the previous result set.

### Open content

Visitors can select a displayed card or link to open the verified HTTPS URL in a new browser tab. The voice agent does not upload, edit, delete, or expose private files.

### Voice interaction

- Microphone capture through the browser
- AssemblyAI speech recognition
- AssemblyAI turn detection
- Natural interruption while the agent is speaking
- AssemblyAI speech output using the selected voice
- Current voice: `james`
- Browser loudspeaker routing where the device/browser supports it
- Visible listening, thinking, speaking, and error states
- Visible user transcript for interaction feedback
- Spoken agent responses are not duplicated as large response text in the UI

## Owner mode

Owner mode is disabled by default and is never shown as an always-visible PIN form.

### Unlock flow

1. Mike says or selects an owner action, such as “Update my profile picture.”
2. The backend determines that the requested action requires owner authorization.
3. The backend sends a `pin_required` event to the browser.
4. The UI reveals a focused PIN prompt.
5. Mike enters the PIN locally in the browser.
6. The PIN is sent directly to the backend over the protected connection.
7. The backend verifies the PIN and creates a short-lived owner session.
8. The requested action is retried or shown as ready for confirmation.

The PIN must never be sent to AssemblyAI, included in the voice transcript, passed to a tool, or spoken aloud by the agent.

### Owner-mode controls

The owner UI should provide:

- Clear owner-mode status
- Session expiry indication
- Lock owner mode immediately
- Cancel the current operation
- Revoke access after a failed or completed action
- Confirmation before destructive or irreversible changes

Owner authorization must be checked server-side for every write. A frontend flag alone is not authorization.

## Admin actions

### Profile

Mike can:

- Update display name
- Update tagline
- Update location
- Update focus or professional direction
- Update experience summary
- Update availability status
- Update availability detail
- Update About/profile narrative
- Update profile picture

Profile-picture flow:

1. Enter owner mode.
2. Request “Update my profile picture.”
3. The UI opens a file picker or drag-and-drop target.
4. The selected image is uploaded through the protected backend upload path.
5. The backend validates type and size, stores the asset, and updates the profile asset reference.
6. The UI shows a preview and confirmation.

### CV

Mike can:

- Upload a replacement CV PDF
- Replace the currently published CV
- Remove or unpublish the current CV
- View the currently configured CV
- Update CV-related metadata such as label or description

The UI must show file type, file size, upload progress, validation errors, and a confirmation before replacing the current CV.

### Projects

Mike can create, edit, publish, unpublish, reorder, and delete projects.

Editable project fields may include:

- Title
- Slug
- Tagline or short description
- Full description/details
- Project status
- Project type/platform
- Technologies and tags
- Repository URL
- Live/demo URL
- Card image
- Gallery images
- Featured status
- Visibility
- Custom order
- Publication date or year

### Articles

Mike can:

- Create an article entry
- Edit title, description, tags, date, and link
- Update article media
- Publish or unpublish an article
- Mark an article as featured
- Reorder articles
- Delete an article

### Hackathons and events

Mike can:

- Create hackathon or event entries
- Edit titles, descriptions, results, dates, locations, and links
- Update associated images or galleries
- Publish or unpublish entries
- Mark entries as featured
- Reorder entries
- Delete entries

### Skills and education

Mike can:

- Add, edit, reorder, hide, or remove skill groups
- Add, edit, reorder, hide, or remove individual skill values
- Update education records
- Update degree, school, dates, description, and ordering

### Certificates

Mike can:

- Upload a certificate image or document
- Update certificate title and metadata
- Publish or unpublish a certificate
- Reorder certificates
- Replace a certificate file
- Delete a certificate

### Bucket list

Mike can:

- Add a bucket-list item
- Edit its title and remark
- Mark it complete or incomplete
- Reorder items
- Delete an item

### Contact and professional links

Mike can:

- Add a public contact or professional link
- Edit its label, URL, category, and handle
- Reorder links
- Hide or show links
- Delete links

## Media picker functionality

The media picker is used whenever an admin action needs a file.

It should support:

- Selecting an image, PDF, or other explicitly allowed file type
- File type validation
- File-size validation
- Preview before upload
- Upload progress
- Cancel upload
- Retry after failure
- Explicit upload confirmation
- Clear success or failure result

Media travels directly from the browser to the protected backend upload path. The voice model only receives a high-level result such as “upload completed”; it never receives the file bytes or PIN.

## Suggested browser events

The voice WebSocket can emit these UI events:

- `ready` — voice session is ready
- `listening` — waiting for the visitor or owner to speak
- `thinking` — processing a request
- `speaking` — playing the agent response
- `transcript` — user speech transcript, with final/interim status
- `actions` — verified public cards or links
- `pin_required` — reveal the owner PIN prompt
- `owner_unlocked` — owner session established
- `owner_locked` — owner session ended or expired
- `upload_requested` — show the media picker
- `upload_progress` — update upload progress
- `confirmation_required` — show a save/delete confirmation
- `operation_succeeded` — show the completed admin action
- `operation_failed` — show a recoverable error
- `error` — voice or connection failure

## UI states to design

The visual skin should account for:

1. Idle landing state
2. Microphone permission request
3. Listening state
4. Interim transcript state
5. Thinking/tool-use state
6. Speaking state
7. Public result state with grouped cards
8. Empty result state
9. Voice or network error state
10. Owner action detected, PIN hidden
11. PIN prompt visible
12. Incorrect PIN or lockout state
13. Owner mode unlocked
14. Media picker visible
15. Uploading state
16. Upload preview and confirmation
17. Save confirmation
18. Successful update state
19. Owner session expired or manually locked

## Security boundaries

- Public reads are available without owner authorization.
- All writes require a valid short-lived owner session.
- The backend validates owner authorization for every write.
- The PIN is stored as a secure hash, never plaintext.
- Failed PIN attempts are rate-limited and temporarily locked out.
- The PIN is not sent to AssemblyAI or any LLM/tool call.
- Uploaded media is validated by the backend.
- Only approved HTTPS media URLs are emitted to public visitors.
- Destructive actions require explicit confirmation.
- Owner mode automatically expires after inactivity.
- Locking owner mode immediately invalidates the owner session.

## Current MVP boundary

The current hackathon version is public, read-only, and focused on AssemblyAI Voice Agent interaction. The owner PIN flow and admin write operations are the next protected capability layer. Public browsing, verified media display, and voice responses must remain functional if owner mode is unavailable.


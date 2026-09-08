# Portfolio Owner Onboarding

Use this guide after cloning the application to make it recognize a new owner and populate that
owner's portfolio data.

The application does not identify an owner from their name, username, or message content. Owner
authorization comes from the Telegram numeric user ID configured in `ADMIN_TELEGRAM_ID`. The LLM
then receives the sender's name and authorization status as trusted request context.

## 1. Configure the owner

Copy the environment template and set the real values:

```bash
cp .env.example .env
```

At minimum, configure:

- `DATABASE_URL`
- `SERVICE_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `ADMIN_TELEGRAM_ID`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `BACKEND_URL`
- R2 credentials for file uploads

To find the Telegram ID, send a message to the bot and inspect the Telegram update payload or use
a trusted Telegram ID lookup bot. Put the numeric ID in `ADMIN_TELEGRAM_ID`, not the username.

## 2. Create the database

Run migrations from the repository virtual environment:

```bash
.venv/bin/alembic -c backend/alembic.ini upgrade head
```

Start the backend and bot, then verify:

```bash
curl http://127.0.0.1:8000/health
```

The production deployment must use an HTTPS Telegram webhook and the same database for the backend
and bot.

## 3. Introduce the owner to the assistant

Open the bot from the Telegram account whose ID is configured in `ADMIN_TELEGRAM_ID` and send:

```text
/start
```

The welcome message should use the Telegram first and last name dynamically. It should not require
the owner to identify themselves in a prompt.

If the bot treats the owner as a visitor, stop and fix `ADMIN_TELEGRAM_ID` before adding data.

## 4. Populate identity and profile data

Send ordinary-language requests. Start with the owner's basic profile:

```text
Set my name to Jane Doe, tagline to Backend engineer, location to Nairobi, and focus to reliable AI products.
```

Then add the longer profile fields:

```text
Set my about text to [the owner's verified biography].
Set my experience and availability details to [verified text].
```

Profile updates are partial. Only fields explicitly requested should change.

## 5. Add contact and social links

Provide all verified links in ordinary language:

```text
Set my WhatsApp and Telegram usernames to janedoe, my GitHub username to janedoe, and my dev.to username to janedoe.
```

The assistant assigns default categories per platform, but categories can be explicit:

```text
Add my GitHub profile as a professional link and my WhatsApp as a contact link.
```

Repeat requests are safe because normalized links are upserted.

## 6. Add the base CV

Attach the CV file and tell the assistant what it is:

```text
This is my current base CV. Store it as my CV and use it for future tailoring.
```

The file is stored as an asset. The CV base data used for tailoring must contain verified profile,
experience, education, skills, project, and qualification information. Do not rely on the LLM to
invent missing sections.

The upload limit is 5 MB. PDFs are not automatically sent to the LLM during ordinary asset
listing; they are handled by the specific CV workflow.

## 7. Populate portfolio content

Add projects and other content in batches, using complete verified information:

```text
Add the Vela project with its title, summary, status, category, dates, technologies, repositories, demo links, and project details: [content]
```

For each project, add normalized relationships and rich content separately when needed:

```text
Add Kotlin, Python, and FastAPI technologies to Vela.
Add https://github.com/janedoe/vela as Vela's primary repository.
Add a Vela metric: [label and value].
Add a Vela architecture decision: [title and explanation].
```

The LLM resolves existing project and technology records before writing relationships. Repositories,
technologies, and links should be upserted rather than duplicated.

## 8. Upload media

Request the intended upload in natural language:

```text
I need to change my profile picture.
I want to add a gallery image to the Vela project.
I want to upload my Backend Engineering certificate.
```

Attach the file when requested. For project media, follow up with its role if necessary:

```text
Attach that asset to Vela as a gallery image.
```

Use descriptive labels, captions, and alt text so the frontend and independent project sites can
present the assets well.

## 9. Generate role policies

After the CV and portfolio are populated, ask the assistant to derive supported role families:

```text
Analyze my current CV and portfolio data and propose supported role policies.
```

The LLM creates conservative pending policies from verified evidence. Review them:

```text
List my role policies.
```

Activate only the policies that accurately describe the owner's evidence:

```text
Activate the backend engineering and mobile development policies.
```

Policies are dynamic database records. They are not determined by a hardcoded list of job titles.

## 10. Verify CV tailoring

Paste a complete job description without a command prefix:

```text
[paste the job description]
```

The assistant should recognize it, compare it against the verified CV and active role policies, and
show a proposed summary, projects, and skills. Revise it naturally or approve it with the inline
button. The base CV must remain unchanged.

Test more than one technical family, such as backend, mobile, DevOps, ICT support, or data roles.
The assistant should assess each role against stored evidence rather than rejecting it because the
title differs from the owner's current profile.

## 11. Verification checklist

- `/start` greets the owner using dynamic profile/Telegram data.
- A non-owner can read public content but cannot write.
- Profile updates preserve unspecified fields.
- Link creation and repetition do not create duplicates.
- Project, repository, and technology relationships use exact records.
- Assets upload under 5 MB and can be attached to projects.
- Gallery items can be listed and viewed.
- Role policies are initially pending and inactive.
- Active policies influence CV tailoring.
- Tailored CV rendering does not overwrite the base CV.
- Failed writes show the backend reason and remain retryable.

For routine management, use `backend/DATA_MANAGEMENT_MANUAL.md`. This document is only for
initial setup of a new clone and its owner.

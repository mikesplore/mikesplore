# Mikesplore Application Purpose

Mikesplore is a backend-driven portfolio platform. PostgreSQL is the source of truth for the
profile, projects, articles, events, hackathons, skills, links, certificates, CV data, and other
portfolio content. The FastAPI backend exposes public read endpoints to the website and protected
write endpoints for administrative changes. The React frontend loads portfolio content at runtime
instead of bundling the content into the build.

The Telegram bot is a second client of the same backend:

- Visitors can ask free-form questions. The Groq-powered LLM uses backend tools to ground answers
  in current portfolio data; it does not access the database directly.
- Visitors can use deterministic inline-button browsing for projects, articles, events, skills,
  certificates, contact links, and other public sections.
- The portfolio owner can manage content through natural-language requests interpreted by the LLM,
  or through the deterministic `/manage` interactive wizard. Writes require the owner Telegram ID,
  a preview/confirmation where applicable, and the backend service key.
- The owner can upload assets, maintain the base CV, tailor it to a job description, review the
  proposed changes, and explicitly generate a PDF. The Generate button calls the backend directly
  using the already-approved patch; it does not spend another LLM turn.

The bot never talks to PostgreSQL directly. This keeps the frontend, Telegram bot, and future
clients on the same API, validation rules, visibility controls, and source of truth.

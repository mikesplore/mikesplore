# Mikesplore

> **The digital showcase and interactive AI assistant for Michael Odhiambo.**  
> Full-stack systems, production projects, technical writing, and live interactive AI workflows.

<p align="center">
  <a href="https://mikesplore.me"><strong>Visit Website (mikesplore.me)</strong></a> •
  <a href="https://t.me/mikesplorebot"><strong>Chat with @mikesplorebot</strong></a>
</p>

<p align="center">
  <img src="https://readme-stats-github.pages.dev/api?username=mikesplore&theme=dark" alt="GitHub Stats" />
</p>

---

## What's Inside?

Explore the full interactive platform directly on **[mikesplore.me](https://mikesplore.me)**:

* **Featured Work & Architecture:** In-depth case studies of full-stack, AI, and mobile systems.
* **Articles & Insights:** Technical write-ups on software engineering, API design, and DevOps.
* **Hackathons & Milestones:** Event breakdowns, awards, and local developer community involvement.
* **Interactive Telegram Assistant:** Ask [@mikesplorebot](https://t.me/mikesplorebot) questions about my work, request a tailored CV, or explore grounded portfolio data in real time.

---

## Tech Stack Overview

Built with **React**, **FastAPI**, **PostgreSQL**, **Groq LLM Tool Calling**, **Telegram Bot API**, and **Cloudflare R2**.

---

## Local Setup

```bash
# Clone and set up backend dependencies
pip install -r requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload

# Run frontend (from /frontend directory)
npm install
npm run dev

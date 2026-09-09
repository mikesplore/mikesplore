-- Curated project seed generated from the public mikesplore GitHub repositories.
-- Apply after `alembic upgrade head`:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/data/seed_projects.sql
--
-- This is intentionally curated for a job-facing portfolio. It does not import
-- every repository, fork, tutorial, or abandoned experiment.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Technologies are normalized so they can be shown and edited independently.
INSERT INTO technologies (id, name, category)
VALUES
  (gen_random_uuid(), 'Python', 'language'),
  (gen_random_uuid(), 'FastAPI', 'backend'),
  (gen_random_uuid(), 'WebSocket', 'backend'),
  (gen_random_uuid(), 'MCP', 'ai'),
  (gen_random_uuid(), 'AI agents', 'ai'),
  (gen_random_uuid(), 'Kotlin', 'language'),
  (gen_random_uuid(), 'Jetpack Compose', 'frontend'),
  (gen_random_uuid(), 'React', 'frontend'),
  (gen_random_uuid(), 'TypeScript', 'language'),
  (gen_random_uuid(), 'Next.js', 'frontend'),
  (gen_random_uuid(), 'PostgreSQL', 'database'),
  (gen_random_uuid(), 'Redis', 'database'),
  (gen_random_uuid(), 'Docker', 'devops'),
  (gen_random_uuid(), 'Paystack', 'payments'),
  (gen_random_uuid(), 'Gemini', 'ai'),
  (gen_random_uuid(), 'Genkit', 'ai'),
  (gen_random_uuid(), 'Django', 'backend'),
  (gen_random_uuid(), 'Room', 'android'),
  (gen_random_uuid(), 'MVVM', 'architecture')
ON CONFLICT (name) DO UPDATE SET category = EXCLUDED.category;

-- Entries are upserts by slug, making this file safe to re-run after editing.
INSERT INTO entries (id, slug, content_type, title, blurb, tags, source, is_visible, is_featured, custom_order, status, category, origin)
VALUES
  (gen_random_uuid(), 'vela', 'project', 'Vela',
   'Designed and built a secure remote-computing ecosystem for controlling Linux workstations from mobile clients, web clients, and AI assistants. The core FastAPI agent exposes typed capabilities for files, processes, Docker, displays, audio, power, notifications, monitoring, and automation. An outbound WebSocket tunnel avoids requiring inbound ports on home networks, while JWT authentication, bcrypt credentials, filesystem allowlists, rate limits, and systemd services protect the host. The wider system includes a multi-tenant VPS relay, MCP bridge, Android controller, and web client.',
   ARRAY['Linux', 'remote systems', 'AI agents', 'MCP', 'infrastructure'], '{"provider":"github","curated":true}', true, true, 10, 'active', 'Infrastructure and AI', 'github'),
  (gen_random_uuid(), 'gatekeeperd', 'project', 'Gatekeeperd',
   'Built an open-source platform for operating self-hosted client applications as paid services. Gatekeeperd sits behind Nginx or Traefik, evaluates client access at the edge, and routes active customers through while presenting a Paystack self-service paywall to overdue or blocked customers. Payment webhooks can restore access automatically. The system combines a Kotlin backend, PostgreSQL and Redis-backed runtime dependencies, Docker-aware project operations, JWT-protected administration, audit history, and a separate React/TypeScript dashboard for managing deployments, billing state, and access control.',
   ARRAY['access control', 'payments', 'SaaS infrastructure', 'Docker', 'Kotlin'], '{"provider":"github","curated":true}', true, true, 20, 'active', 'SaaS infrastructure', 'github'),
  (gen_random_uuid(), 'scribed', 'project', 'Scribed',
   'Built the document and client-operations service for a freelance platform. Scribed turns contract and invoice data into numbered, verifiable PDF documents, persists their lifecycle, delivers them through Resend, and exposes Telegram workflows for operational management. Its boundary is deliberately separate from Gatekeeperd: Scribed owns contracts, invoices, verification, and delivery, while Gatekeeperd owns hosted projects, payments, access control, and Paystack events. This separation keeps billing enforcement and document operations independently deployable while allowing both systems to work together.',
   ARRAY['document automation', 'PDF', 'freelance operations', 'Telegram', 'Resend'], '{"provider":"github","curated":true}', true, true, 30, 'active', 'Business automation', 'github'),
  (gen_random_uuid(), 'mikesplore', 'project', 'Mikesplore Portfolio Platform',
   'Rebuilt a static portfolio into a database-driven content platform. The React frontend consumes runtime APIs from a modular FastAPI backend backed by PostgreSQL, Alembic migrations, and Cloudflare R2 for uploaded media. A Telegram assistant provides grounded public search over verified portfolio data and a protected administrative workflow for previews, confirmations, content updates, CV operations, and asset uploads. The system includes service-key authentication, visibility filtering, normalized technologies and repositories, project content blocks, pagination metadata, provider-error handling, and token-usage telemetry for the LLM layer.',
   ARRAY['FastAPI', 'React', 'PostgreSQL', 'Telegram', 'LLM tools', 'Cloudflare R2'], '{"provider":"github","curated":true}', true, true, 40, 'active', 'Web platform', 'github'),
  (gen_random_uuid(), 'coastech', 'project', 'Coastech Commerce Platform',
   'Built a direct-to-consumer commerce platform around Medusa and Next.js. The storefront covers product discovery, cart and checkout flows, customer accounts, and order tracking, while Paystack handles local payment integration. The project also includes operational administration capabilities for managing products and orders, demonstrating the full path from customer-facing commerce UI through backend commerce primitives and payment confirmation.',
   ARRAY['e-commerce', 'Next.js', 'Medusa', 'Paystack', 'TypeScript'], '{"provider":"github","curated":true}', true, true, 50, 'active', 'E-commerce', 'github'),
  (gen_random_uuid(), 'pwanipulse', 'project', 'PwaniPulse',
   'Built a multilingual, multimodal civic-intelligence prototype for constituency offices. PwaniPulse accepts the formats citizens already use—Swahili or English text, photos, and voice notes—then uses Gemma function calling to split one message into independent issues, classify themes and wards, score urgency, surface recurring patterns, and generate an evidence-backed brief for public action. The workflow turns unstructured citizen reports into a ranked operational view instead of rewarding only the loudest or most organized request.',
   ARRAY['Gemma', 'AI', 'civic technology', 'multilingual', 'Mombasa'], '{"provider":"github","curated":true}', true, true, 60, 'active', 'AI and civic technology', 'github'),
  (gen_random_uuid(), 'quizbase', 'project', 'QuizBase',
   'Built a retrieval-locked study assistant that searches Quizlet through Google Custom Search and returns the exact answer from retrieved flashcards. The application deliberately refuses to generate an answer from model memory: when the source cannot be found, it reports that the answer is unavailable. This project demonstrates a practical anti-hallucination design in which retrieval, source boundaries, and failure behavior are part of the product contract.',
   ARRAY['retrieval-augmented generation', 'anti-hallucination', 'Quizlet', 'TypeScript'], '{"provider":"github","curated":true}', true, false, 70, 'active', 'AI application', 'github'),
  (gen_random_uuid(), 'github-wrapped', 'project', 'Git Roast Wrapped',
   'Built an AI-powered GitHub year-in-review application that turns repository activity into an interactive, mobile-first story. It authenticates through GitHub OAuth when deeper access is needed, fetches repository and commit statistics, ranks projects and languages, generates data-backed commentary with Gemini, and presents the results across animated Spotify-Wrapped-style slides. The design combines API integration, authentication, data transformation, visualization, and controlled generative output in one user-facing workflow.',
   ARRAY['Next.js', 'Gemini', 'GitHub API', 'data visualization', 'TypeScript'], '{"provider":"github","curated":true}', true, false, 80, 'active', 'AI application', 'github'),
  (gen_random_uuid(), 'timetable', 'project', 'Timetable Generator',
   'Developed a timetable-generation system that models academic scheduling as a constraint problem rather than manual spreadsheet editing. The Kotlin implementation focuses on producing workable schedules from competing academic requirements, with related web and multiplatform clients in the repository family. The project demonstrates algorithmic problem solving, domain modelling, and the separation of scheduling logic from client presentation.',
   ARRAY['Kotlin', 'algorithms', 'constraint solving', 'multiplatform'], '{"provider":"github","curated":true}', true, false, 90, 'active', 'Algorithms and mobile', 'github'),
  (gen_random_uuid(), 'uni-connect', 'project', 'Uni-Connect',
   'Built a student-management and campus collaboration application for resource sharing, discussions, attendance tracking, announcements, and course materials. The Android implementation uses Kotlin, Jetpack Compose, MVVM, and Room to organize UI state, domain behavior, and local persistence. It reflects a practical mobile architecture for a multi-feature product rather than a single-screen prototype.',
   ARRAY['Kotlin', 'Android', 'MVVM', 'student systems'], '{"provider":"github","curated":true}', true, false, 100, 'active', 'Mobile applications', 'github')
ON CONFLICT (slug) DO UPDATE SET
  title = EXCLUDED.title, blurb = EXCLUDED.blurb, tags = EXCLUDED.tags,
  source = EXCLUDED.source, is_visible = EXCLUDED.is_visible,
  is_featured = EXCLUDED.is_featured, custom_order = EXCLUDED.custom_order,
  status = EXCLUDED.status, category = EXCLUDED.category, origin = EXCLUDED.origin,
  updated_at = now();

-- Repository records preserve the actual implementation boundaries of larger products.
INSERT INTO repositories (id, entry_id, name, url, is_visible, is_primary, custom_order, role_label, primary_language, link_label, synced_from_github)
VALUES
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='vela'), 'vela', 'https://github.com/mikesplore/vela', true, true, 10, 'Linux agent and FastAPI control plane', 'Python', 'View source', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='vela'), 'velavps', 'https://github.com/mikesplore/velavps', true, false, 20, 'Multi-tenant VPS relay and tunnel broker', 'Python', 'Relay service', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='vela'), 'vela-mcp', 'https://github.com/mikesplore/vela-mcp', true, false, 30, 'MCP tool bridge for AI clients', 'Python', 'MCP bridge', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='vela'), 'vela-android', 'https://github.com/mikesplore/vela-android', true, false, 40, 'Android remote-control client', 'Kotlin', 'Android client', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='vela'), 'vela-chat', 'https://github.com/mikesplore/vela-chat', true, false, 50, 'Web client', 'TypeScript', 'Web client', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='gatekeeperd'), 'gatekeeperd', 'https://github.com/mikesplore/gatekeeperd', true, true, 10, 'Payment gating API and deployment engine', 'Kotlin', 'Backend', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='gatekeeperd'), 'gatekeeperd-frontend', 'https://github.com/mikesplore/gatekeeperd-frontend', true, false, 20, 'React administration dashboard', 'TypeScript', 'Dashboard', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='scribed'), 'scribed', 'https://github.com/mikesplore/scribed', true, true, 10, 'Contracts, invoices, PDF delivery, and Telegram workflows', 'Python', 'Backend', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='mikesplore'), 'mikesplore', 'https://github.com/mikesplore/mikesplore', true, true, 10, 'Portfolio monorepo', 'Python', 'Source code', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='coastech'), 'coastech', 'https://github.com/mikesplore/coastech', true, true, 10, 'Medusa and Next.js commerce platform', 'TypeScript', 'Source code', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='pwanipulse'), 'pwanipulse', 'https://github.com/mikesplore/pwanipulse', true, true, 10, 'Civic intelligence notebook and dashboard', 'Python', 'Source code', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='quizbase'), 'quizbase', 'https://github.com/mikesplore/quizbase', true, true, 10, 'Retrieval-locked assistant', 'TypeScript', 'Live project', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='github-wrapped'), 'github-wrapped', 'https://github.com/mikesplore/github-wrapped', true, true, 10, 'GitHub analytics and AI storytelling app', 'TypeScript', 'Live project', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='timetable'), 'Timetable', 'https://github.com/mikesplore/Timetable', true, true, 10, 'Schedule-generation algorithm', 'Kotlin', 'Source code', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='timetable'), 'Timetable-web', 'https://github.com/mikesplore/Timetable-web', true, false, 20, 'Web client', 'JavaScript', 'Web client', true),
  (gen_random_uuid(), (SELECT id FROM entries WHERE slug='uni-connect'), 'Uni-Connect', 'https://github.com/mikesplore/Uni-Connect', true, true, 10, 'Student management Android application', 'Kotlin', 'Source code', true)
ON CONFLICT (url) DO UPDATE SET
  entry_id = EXCLUDED.entry_id, name = EXCLUDED.name, is_visible = EXCLUDED.is_visible,
  is_primary = EXCLUDED.is_primary, custom_order = EXCLUDED.custom_order,
  role_label = EXCLUDED.role_label, primary_language = EXCLUDED.primary_language,
  link_label = EXCLUDED.link_label, synced_from_github = EXCLUDED.synced_from_github;

-- Attach normalized technologies to each curated project.
INSERT INTO entry_technologies (entry_id, technology_id)
SELECT e.id, t.id FROM entries e CROSS JOIN technologies t
WHERE (e.slug, t.name) IN (
  ('vela','Python'), ('vela','FastAPI'), ('vela','WebSocket'), ('vela','MCP'), ('vela','AI agents'), ('vela','Docker'),
  ('gatekeeperd','Kotlin'), ('gatekeeperd','PostgreSQL'), ('gatekeeperd','Redis'), ('gatekeeperd','Paystack'), ('gatekeeperd','Docker'),
  ('scribed','Python'), ('scribed','FastAPI'), ('scribed','PostgreSQL'),
  ('mikesplore','Python'), ('mikesplore','FastAPI'), ('mikesplore','React'), ('mikesplore','PostgreSQL'), ('mikesplore','Docker'),
  ('coastech','TypeScript'), ('coastech','Next.js'), ('coastech','Paystack'),
  ('pwanipulse','Python'), ('pwanipulse','AI agents'),
  ('quizbase','TypeScript'), ('quizbase','AI agents'),
  ('github-wrapped','TypeScript'), ('github-wrapped','Next.js'), ('github-wrapped','Gemini'),
  ('timetable','Kotlin'), ('uni-connect','Kotlin'), ('uni-connect','MVVM'), ('uni-connect','Room')
)
ON CONFLICT DO NOTHING;

COMMIT;

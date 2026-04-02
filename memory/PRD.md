# PRD — Field Quality Capture & Review System

_Date updated: 2026-04-02_

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training. The system supports: no-login crew capture, management and owner dashboards, CSV/API-ready job import, rubric versioning, Supabase-backed image storage, JSONL/CSV exports, analytics, audit history, and workflow states.

## Architecture
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload
- Database: MongoDB (app-managed string IDs)
- Storage: Supabase Storage (backend service role)
- **Modularized backend:**
  - `server.py` (~2614 lines) — route handlers + seed + app setup
  - `shared/deps.py` (~400 lines) — all utilities, auth deps, business logic, storage helpers
  - `shared/models.py` (~170 lines) — Pydantic schemas
  - `routes/` — directory ready for future granular route extraction

## What's Implemented

### Core (prior sessions)
- Full crew capture portal with QR access, multi-photo upload, GPS, Supabase Storage
- JWT auth with seeded demo accounts and role-based navigation
- Job import + QR management workspace
- Management/Owner review queues with rubric scoring
- Exports workspace (JSONL/CSV), Analytics dashboard
- Standards Library, Repeat Offenders, Training Mode
- Equipment Maintenance logs with Red-Tag notification flow
- Dynamic Rubric Matrix CRUD + Quick Matrix Ref widget
- Strict mobile Rapid Review with progress bar, timer, speed alerts
- Login Page Admin/Crew split, theme toggle on Settings
- Role-filtered dashboard (Owner/GM see all stats; others see subset)
- Jobs page toggle sections, Crew QR update button
- Repeat Offenders: collapsible heatmap, standard courses of action, carousel
- Separate Damage (amber) & Incident (red, OSHA) reporting in crew portal

### 2026-04-02 Session (Current)
- **Backend modularization (Phase 1):** Extracted ~580 lines of utility functions, constants, auth dependencies, business logic, and storage helpers from `server.py` into `shared/deps.py`. All route handlers now import from `shared.deps` instead of defining functions inline. `server.py` reduced from 3195 to 2614 lines.
- **Standards Library pagination:** Limited to 5 items per page with Prev/Next pagination controls. Replaces previous full-load carousel.
- **Standard detail popup (admin):** Clicking any standard card opens a full-detail popup showing image, category, division targets, crew notes, admin notes, checklist, training question with options/answer, shoutout, and training status.
- **Standard detail popup (crew):** Tapping a standard in the Crew Capture Standards tab opens a detail overlay with image, title, category, description, and X close button.

## Seeded Accounts
All passwords: SLMCo2026!
- Supervisors: hjohnny.super@slmco.local, scraig.super@slmco.local, pfran.super@slmco.local
- Account Managers: kscott.accm@slmco.local, bmegan.accm@slmco.local, mdaniel.accm@slmco.local
- Production Managers: atim.prom@slmco.local, ozach.prom@slmco.local, wscott.prom@slmco.local
- GMs: ctyler.gm@slmco.local, sbrad.gm@slmco.local
- Owner: sadam.owner@slmco.local

## Prioritized Backlog

### P1
- Reviewer Performance Dashboard (per-reviewer speed trends, accuracy, calibration drift)
- Continue server.py modularization Phase 2 (extract route handlers into individual files in routes/)
- Owner random sampling filters and variance drilldowns

### P2
- AI-assisted scoring (recommend rubric scores before human confirmation)
- Automated quality checks from rubric dataset (AI training pipeline)
- Closed-loop coaching system (auto-generate training from repeat offenders)
- Staff password reset / invite flows
- Offline tolerance for field crews
- Granular audit viewer, reviewer activity history
- Bulk export filters and scheduled export jobs

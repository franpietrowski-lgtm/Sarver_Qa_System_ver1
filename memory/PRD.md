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
  - `server.py` (~2570 lines) — route handlers + seed + app setup
  - `shared/deps.py` (~520 lines) — all utilities, auth deps, business logic, storage helpers
  - `shared/models.py` (~170 lines) — Pydantic schemas

## What's Implemented

### Core (prior sessions)
- Full crew capture portal with QR access, multi-photo upload, GPS, Supabase Storage
- JWT auth with seeded demo accounts and role-based navigation
- Job import + QR management workspace, Management/Owner review queues with rubric scoring
- Exports workspace (JSONL/CSV), Analytics dashboard
- Standards Library with pagination (5/page) + detail popups, Repeat Offenders, Training Mode
- Equipment Maintenance logs with Red-Tag notification flow
- Dynamic Rubric Matrix CRUD + Quick Matrix Ref widget
- Strict mobile Rapid Review with progress bar, timer, speed alerts
- Login Page Admin/Crew split, theme toggle on Settings
- Role-filtered dashboard, Jobs page toggle sections, Crew QR update button
- Repeat Offenders: collapsible heatmap, standard courses of action, carousel
- Separate Damage (amber) & Incident (red, OSHA) reporting in crew portal
- Backend modularized: helpers/business logic extracted to shared/deps.py

### 2026-04-02 Session (Current)
- **Work date capture:** Added `work_date` field to crew submission form (date picker defaulting to today) and backend endpoint. Stored as YYYY-MM-DD.
- **Work date display:** `work_date` shown on Overview dashboard submission cards, admin ReviewPage submission list, and detail view.
- **Rich test data:** Seeded 23 submissions spread across 8 months (2-242 days ago) with 5 different crews, varied issue types, and rapid reviews. This populates the repeat offender heatmap with realistic escalation patterns.
- **Repeat offender window validation:** Changing the day value input now shows meaningful escalation differences — 30-day window: 2 crews; 90-day: 4 crews; 240-day: 5 crews with Critical/Warning/Watch levels.

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
- Continue server.py modularization Phase 2 (extract route handlers into individual files)
- Owner random sampling filters and variance drilldowns

### P2
- AI-assisted scoring, Closed-loop coaching from repeat offenders
- Staff password reset / invite flows, Offline tolerance
- Granular audit viewer, Bulk export filters

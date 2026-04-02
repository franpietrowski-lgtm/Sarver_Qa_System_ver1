# PRD — Field Quality Capture & Review System

_Date updated: 2026-04-01_

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training. The system supports: no-login crew capture, management and owner dashboards, CSV/API-ready job import, rubric versioning, Supabase-backed image storage, JSONL/CSV exports, analytics, audit history, and workflow states.

## Architecture
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload
- Database: MongoDB (app-managed string IDs)
- Storage: Supabase Storage (backend service role)
- Models extracted to `/app/backend/shared/models.py`
- Route modules structure: `/app/backend/routes/`, `/app/backend/shared/`

## What's Implemented

### Core (prior sessions)
- Full crew capture portal with QR access, multi-photo upload, GPS, Supabase Storage
- JWT auth with seeded demo accounts and role-based navigation
- Job import + QR management workspace
- Management/Owner review queues with rubric scoring
- Exports workspace (JSONL/CSV), Analytics dashboard
- Standards Library, Repeat Offenders, Training Mode
- Equipment Maintenance logs with Red-Tag notification flow
- Unified login screen, theme toggler, pagination

### 2026-04-01 Session 1-3
- Dynamic Rubric Matrix CRUD + Quick Matrix Ref widget
- Strict mobile Rapid Review with progress bar, timer, speed alerts
- Rubric Matrix Editor page with visual weight sliders
- Dashboard tightened to single-page layout
- Pydantic models extracted to shared/models.py
- Login Page Admin/Crew split, AppShell simplified, Theme Toggle to Settings
- Backend seed with standardized lowercased emails

### 2026-04-01 Session 4
- Fixed OverviewPage crash (missing imports/undefined vars)
- Fixed backend email seeding (lowercased for case-insensitive login)
- Standards Library rewrite: toggle sections for Authoring/Equipment, horizontal carousel
- Equipment Records on Standards page under toggle section
- Repeat Offender threshold description (Watch 3+/Warning 5+/Critical 7+)

### 2026-04-01 Session 5 (Current)
- **Role-filtered Dashboard** — Owner Queue and Export Ready stat cards hidden for non-Owner/non-GM roles. Workflow lifecycle steps filtered by role.
- **Jobs/Alignment page toggles** — Active Crew Links, Inactive Crew Links, and Imported Jobs wrapped in collapsible toggle sections with Framer Motion animation. Active is open by default; others collapsed.
- **Crew QR Update button** — Each active crew link card has an Edit pencil button that opens an inline update form in the Crew QR Control section. Supports label, truck, division, assignment changes via PATCH endpoint.
- **Repeat Offenders overhaul** — Heatmap is now collapsible. New "Standard Courses of Action" card showing Watch/Warning/Critical tier definitions. Crew training recommendations displayed as horizontal carousel. Copy Link button removed; workflow directs to Standards Library for link retrieval.
- **Separate Damage & Incident Reporting (Crew portal)** — Damage reporting (amber): records crew-involved property damage with type selector, location, description, photos. Incident/Accident reporting (red, OSHA-compliant): incident type, date/time, jobsite location, injured person, body part affected, description, treatment given, witness, legal disclaimer notice.

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
- Continue server.py modularization (extract routes into routes/)
- Owner random sampling filters and variance drilldowns

### P2
- AI-assisted scoring (recommend rubric scores before human confirmation)
- Automated quality checks from rubric dataset (AI training pipeline)
- Closed-loop coaching system (auto-generate training from repeat offenders)
- Staff password reset / invite flows
- Offline tolerance for field crews
- Granular audit viewer, reviewer activity history
- Bulk export filters and scheduled export jobs

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

### 2026-04-01 Session 1
- Dynamic Rubric Matrix CRUD API (GET/POST/PATCH/DELETE /api/rubric-matrices)
- Quick Matrix Ref table on dashboard with division filter
- Crew portal icon tabs (Camera/BookOpen/Wrench)
- Strict mobile-only Rapid Review (previous version)
- Dark theme visibility CSS fixes

### 2026-04-01 Session 2
**Phase 1 — Rapid Review Overhaul:**
- Full-screen immersive image with swipe-only rating
- Progress bar with branded color + green glow flash
- Per-image timer, session tracking, speed alerts
- 8s enforced minimum, suspicious fast-swipe flagging

**Phase 2 — Rubric Matrix Editor:**
- New /rubric-editor page with full visual CRUD for GM/Owner
- Visual weight adjustment via drag sliders

**Phase 3 — Dashboard UI Tightening:**
- Compact single-page dashboard layout
- Quick Matrix Ref as clickable widget with popup overlay
- Lifecycle states shown as compact flow chips

**Phase 4 — Server Refactoring + Cross-links:**
- Pydantic models extracted to /app/backend/shared/models.py
- Cross-link navigation cards between Standards, Repeat Offenders, and Rubric Matrices

### 2026-04-01 Session 3
- Login Page redesigned with Admin/Crew split tabs
- AppShell simplified, Theme Toggle moved to Settings page
- Backend seed data updated with standardized email format (lowercased)

### 2026-04-01 Session 4 (Current)
- **Fixed OverviewPage crash** — Missing imports (FolderInput, UploadCloud) and undefined crewLinks reference removed
- **Fixed backend email seeding** — Emails now stored lowercase for case-insensitive login matching
- **Updated test_credentials.md** — All 12 seeded accounts with correct lowercase emails
- **Standards Library page rewrite** — Toggle sections for Authoring and Equipment Records, horizontal carousel for library items using Framer Motion
- **Equipment Records on Standards page** — Paginated equipment logs accessible under a toggle section
- **Repeat Offender threshold description** — Added explanation of Watch (3+), Warning (5+), Critical (7+) levels

## Seeded Accounts
All passwords: SLMCo2026!
- Supervisors: hjohnny.super@slmco.local, scraig.super@slmco.local, pfran.super@slmco.local
- Account Managers: kscott.accm@slmco.local, bmegan.accm@slmco.local, mdaniel.accm@slmco.local
- Production Managers: atim.prom@slmco.local, ozach.prom@slmco.local, wscott.prom@slmco.local
- GMs: ctyler.gm@slmco.local, sbrad.gm@slmco.local
- Owner: sadam.owner@slmco.local

## Prioritized Backlog

### P1
- Continue server.py modularization (extract route handlers into routes/)
- Reviewer Performance Dashboard (per-reviewer speed trends, accuracy, calibration drift)
- Owner random sampling filters and variance drilldowns
- Rubric version history viewer

### P2
- AI-assisted scoring (recommend rubric scores before human confirmation)
- Automated quality checks from rubric dataset (AI training pipeline)
- Closed-loop coaching system (auto-generate training from repeat offenders)
- Staff password reset / invite flows
- Offline tolerance for field crews
- Granular audit viewer, reviewer activity history
- Bulk export filters and scheduled export jobs

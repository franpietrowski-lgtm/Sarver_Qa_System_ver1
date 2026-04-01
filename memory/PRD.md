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

### 2026-04-01 Session 2 (Current)
**Phase 1 — Rapid Review Overhaul:**
- Full-screen immersive image with swipe-only rating (no buttons except exit)
- Progress bar with branded color + green radial glow flash when <15% remain
- Per-image timer displayed in status strip (color-coded by speed)
- Session tracking: POST /api/rapid-review-sessions (start), POST /{id}/complete (end)
- Per-image swipe_duration_ms tracked and stored with each review
- 8s enforced minimum with "take your time" warning, <4s standard/exemplary flagged as suspicious
- Owner speed alert notifications when session has 3+ fast swipes or >30% violation rate
- Concern-swiped items flagged with needs_manual_rescore=true
- GET /api/rapid-reviews/flagged endpoint for concern and fast-flagged reviews
- PATCH /api/rapid-reviews/{id}/rescore endpoint for manual re-scoring
- Session time logs stored in rapid_review_sessions collection

**Phase 2 — Rubric Matrix Editor:**
- New /rubric-editor page with full visual CRUD for GM/Owner
- Create new rubric matrices with service type, division, categories
- Edit existing rubrics: title, division, threshold, min photos, active status
- Visual weight adjustment via drag sliders with auto-redistribution
- Add/remove grading factors dynamically (1-10 factors)
- Activate/deactivate rubrics (soft delete)
- Navigation sidebar shows "Rubric Matrices" for GM and Owner only

**Phase 3 — Dashboard UI Tightening:**
- Compact single-page dashboard layout (reduced card sizes, tighter spacing)
- Quick Matrix Ref as clickable widget that opens popup overlay
- Division filter inside popup, 2-minute auto-close on inactivity
- Lifecycle states shown as compact flow chips instead of large cards
- Rapid Review QR section condensed with smaller QR code

**Phase 4 — Server Refactoring + Cross-links:**
- Pydantic models extracted to /app/backend/shared/models.py
- routes/ and shared/ directories created for modular architecture
- Cross-link navigation cards added to Standards Library and Repeat Offenders pages
- Links to Rubric Matrices, Standards, and Repeat Offenders from each related page

## Prioritized Backlog

### P1
- Continue server.py modularization (extract route handlers into routes/)
- Expand Standards Library with richer media editing
- Expand Repeat Offender tracking with configurable thresholds UI
- Add rubric version history viewer (show all versions, diff changes)
- Persist rapid-review annotations into richer audit artifacts
- Add owner random sampling filters and variance drilldowns

### P2
- AI-assisted scoring (recommend rubric scores before human confirmation)
- Automated quality checks from rubric dataset (AI training pipeline)
- Closed-loop coaching system (auto-generate training from repeat offenders)
- Google social login
- Offline tolerance for field crews
- Granular audit viewer, reviewer activity history
- Bulk export filters and scheduled export jobs
- Staff password reset / invite flows

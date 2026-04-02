# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew**: Mobile field workers submitting photos via QR/link (no login)
- **Management** (Supervisor, PM, AM, GM): Reviews submissions, manages standards
- **Owner**: Final calibration, dataset approval, system oversight

## Core Requirements
- Mobile-first crew portal with division-aware tasking, OSHA incident/damage split, equipment logs
- High-accuracy GPS capture (+/-2m target, soft-warn + flag for reviewers if exceeded)
- Admin/Management dashboard with role-based visibility
- Owner dashboard with calibration heatmap, exports, rubric management
- Tinder-style Rapid Review for fast mobile QA
- Supabase Object Storage for images
- JWT auth with lowercase email standardization
- Role-specific onboarding (Welcome Modal, Getting Started Panel, Help Popovers)

## Tech Stack
- **Frontend**: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB) + JWT Auth
- **Storage**: Supabase Storage (service role)
- **Database**: MongoDB

## Architecture (Post-Modularization)
```
/app/backend/
  server.py              (790 lines — app setup, seed data, router orchestration)
  /shared/
    deps.py              (516 lines — DB, helpers, constants)
    models.py            (170 lines — Pydantic schemas)
  /routes/               (17 modules, ~1980 total lines)
    auth.py, system.py, public.py, submissions.py, equipment.py,
    jobs.py, crew_access.py, users.py, notifications.py, rubrics.py,
    standards.py, reviews.py, rapid_reviews.py, training.py,
    analytics.py, exports.py, integrations.py
```

## What's Been Implemented
- Full crew submission portal with work_date, incident/damage split
- **GPS accuracy polling**: `watchPosition` with `enableHighAccuracy: true`, 10s polling for best reading, color-coded accuracy badges (Precise <=2m / Fair <=5m / Low confidence >5m), "Flagged for review" badge, progress bar animation
- **Backend GPS flag**: `gps_low_confidence: true` on submissions where `gps_accuracy > 2.0`
- Standard and rapid review flows
- Standards library with pagination/popups
- Repeat offender tracking with 8-month seeded heatmap
- Training mode with quiz engine
- Equipment maintenance logs with red-tag notifications
- Dynamic rubric matrix management (CRUD)
- Analytics summary with calibration heatmap
- Dataset exports (CSV/JSONL)
- Supabase image storage (fully integrated)
- Backend modularization Phase 1 + Phase 2 — COMPLETE
- **Role-specific onboarding UI** (Apr 2026):
  - `WelcomeModal`: Role-aware multi-step workflow guide (5 steps for Supervisors, 6 for Owners), localStorage-gated so it only shows on first visit
  - `GettingStartedPanel`: Collapsible quick-start tips panel with role-specific content (4 tips for Management, 5 for Owner)
  - `HelpPopover`: Contextual guide tooltips on key UI elements across OverviewPage, JobsPage, StandardsLibraryPage, CrewCapturePage, AnalyticsPage, RepeatOffendersPage, RubricEditorPage
- **Frontend regression tested**: Iteration 18 — 100% pass on all 7 pages and onboarding components

## Backlog (Prioritized)
- **P1**: Reviewer Performance Dashboard (swipe speed trends, accuracy, calibration drift)
- **P2**: Closed-loop coaching (auto-generated from repeat-offender thresholds)
- **P2**: Owner random sampling filters and variance drilldowns
- **Backlog**: Staff password reset/invite flows
- **Backlog**: AI-assisted scoring and automated quality checks

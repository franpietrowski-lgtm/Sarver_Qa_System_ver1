# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew**: Mobile field workers submitting photos via QR/link (no login)
- **Management** (Supervisor, PM, AM, GM): Reviews submissions, manages standards
- **Owner**: Final calibration, dataset approval, system oversight

## Core Requirements
- Mobile-first crew portal with division-aware tasking, OSHA incident/damage split, equipment logs
- Admin/Management dashboard with role-based visibility
- Owner dashboard with calibration heatmap, exports, rubric management
- Tinder-style Rapid Review for fast mobile QA
- Supabase Object Storage for images
- JWT auth with lowercase email standardization

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
  /routes/               (17 modules, 1979 total lines)
    auth.py              (login, me)
    system.py            (root, health, blueprint)
    public.py            (crew-access, jobs, submissions, equipment-logs, training)
    submissions.py       (files, list, detail, match)
    equipment.py         (list, forward, files)
    jobs.py              (list, CSV import)
    crew_access.py       (CRUD)
    users.py             (list, create, status)
    notifications.py     (list, read)
    rubrics.py           (list, matrices CRUD)
    standards.py         (list, create, update)
    reviews.py           (management, owner)
    rapid_reviews.py     (queue, create, sessions, flagged, rescore)
    training.py          (sessions, repeat offenders)
    analytics.py         (dashboard, analytics summary)
    exports.py           (run, list, download)
    integrations.py      (storage status, drive status)
```

## What's Been Implemented
- Full crew submission portal with work_date, incident/damage split
- Standard and rapid review flows
- Standards library with pagination/popups
- Repeat offender tracking with 8-month seeded heatmap
- Training mode with quiz engine
- Equipment maintenance logs with red-tag notifications
- Dynamic rubric matrix management (CRUD)
- Analytics summary with calibration heatmap
- Dataset exports (CSV/JSONL)
- Supabase image storage (fully integrated)
- Backend modularization Phase 1 (models/helpers) + Phase 2 (routes) — COMPLETE

## Backlog (Prioritized)
- **P1**: Owner random sampling filters and variance drilldowns
- **P2**: Reviewer Performance Dashboard (swipe speed trends, accuracy, calibration drift)
- **P3**: Closed-loop coaching (auto-generated from repeat-offender thresholds)
- **Backlog**: Staff password reset/invite flows
- **Backlog**: AI-assisted scoring and automated quality checks

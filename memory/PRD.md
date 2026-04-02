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
- Multi-theme workspace (6 themes with full CSS variable system)

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
- GPS accuracy polling (10s watchPosition, color-coded badges, backend flag)
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
- Role-specific onboarding UI (WelcomeModal, GettingStartedPanel, HelpPopover)
- **6-Theme System** (Apr 2026):
  - Default (nature green), Dark (forest), Tomboy (navy+pink), Gold (black+gold), Noir (charcoal+crimson), Neon (green+lime)
  - 20+ CSS custom properties per theme:
    - Status tiers: `--status-watch/warning/critical-bg/border/text`
    - Heatmap: `--heat-r/g/b`, `--heat-empty`
    - UI panels: `--panel-gradient-from/to`, `--panel-border`
    - Buttons: `--btn-accent`, `--btn-accent-hover`
    - Forms: `--form-card-bg/border`, `--slider-accent`
    - Badges: `--inactive-badge-bg/text`, `--chip-bg`
    - Modals: `--modal-bg`, `--modal-header-bg`
    - Progress: `--progress-dot-inactive`
    - Text: `--tier-desc-text`
  - Each theme provides ~30% different color/brightness in accent sections
  - Visual theme picker on Settings page with swatch previews

## Backlog (Prioritized)
- **P1**: Reviewer Performance Dashboard (swipe speed trends, accuracy, calibration drift)
- **P2**: Closed-loop coaching (auto-generated from repeat-offender thresholds)
- **P2**: Owner random sampling filters and variance drilldowns
- **Backlog**: Staff password reset/invite flows
- **Backlog**: AI-assisted scoring and automated quality checks

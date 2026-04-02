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
- Multi-theme workspace (6 themes with full Tailwind CSS variable system)

## Tech Stack
- **Frontend**: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB) + JWT Auth
- **Storage**: Supabase Storage (service role)
- **Database**: MongoDB

## Architecture
```
/app/backend/
  server.py              (slim orchestrator)
  /shared/deps.py, models.py
  /routes/               (17 modules)
/app/frontend/src/
  /pages/                (all page components)
  /components/common/    (WelcomeModal, GettingStartedPanel, HelpPopover, StatCard)
  /components/theme/     (ThemeProvider)
  /components/layout/    (AppShell)
  /components/ui/        (Shadcn components)
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
- Backend modularization (17 route files)
- Role-specific onboarding UI
- **Complete 6-Theme System** (Apr 2026):
  - Default (nature green), Dark (forest), Tomboy (navy+pink), Gold (black+gold), Noir (charcoal+crimson), Neon (green+lime)
  - **Tailwind CSS variable overrides**: `--card`, `--card-foreground`, `--popover`, `--popover-foreground`, `--border`, `--muted-foreground`, `--input`, `--accent`, `--accent-foreground`, `--ring`, `--primary`, `--destructive` per theme
  - **Custom CSS variables**: `--status-watch/warning/critical-*`, `--heat-r/g/b`, `--panel-gradient-*`, `--btn-accent`, `--modal-bg`, `--chip-bg`, `--form-card-*`, `--slider-accent`, `--inactive-badge-*`, `--progress-dot-inactive`
  - All Shadcn Card, Popover, Button (outline), Input, and Badge components fully themed
  - ~30% distinct color/brightness per theme across accent sections

## Backlog (Prioritized)
- **P1**: Reviewer Performance Dashboard (swipe speed trends, accuracy, calibration drift)
- **P2**: Closed-loop coaching (auto-generated from repeat-offender thresholds)
- **P2**: Owner random sampling filters and variance drilldowns
- **Backlog**: Staff password reset/invite flows
- **Backlog**: AI-assisted scoring and automated quality checks

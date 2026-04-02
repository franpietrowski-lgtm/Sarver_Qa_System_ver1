# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew**: Mobile field workers submitting photos via QR/link (no login)
- **Management** (Supervisor, PM, AM, GM): Reviews, manages standards, coaching
- **Owner**: Calibration, dataset approval, system oversight, reviewer analytics

## Tech Stack
- **Frontend**: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB) + JWT Auth
- **Storage**: Supabase Storage (service role)
- **Database**: MongoDB

## Architecture
```
/app/backend/
  server.py, /shared/deps.py, /shared/models.py, auth_utils.py
  /routes/ (19 modules)
/app/frontend/src/
  /pages/ (12 pages), /hooks/useIdleTimeout.js
  /components/common/, /components/theme/, /components/layout/, /components/ui/
/app/frontend/public/
  index.html, manifest.json, icon.svg
```

## What's Been Implemented
- Full crew submission portal with work_date, incident/damage split
- GPS accuracy polling (10s watchPosition, color-coded badges, backend flag)
- Standard and rapid review flows
- Standards library, repeat offender tracking, training mode, equipment logs
- Dynamic rubric matrix management, calibration heatmap, dataset exports
- Supabase image storage, backend modularization (19 route files)
- Role-specific onboarding UI (WelcomeModal, GettingStartedPanel, HelpPopover)
- 6 Color Themes + 4 Font Packages (independent of each other)
- Reviewer Performance Dashboard (owner-only)
- Closed-Loop Coaching (auto-generate training for Warning/Critical crews)
- **Staff Password Management** (Apr 2026):
  - Admin password reset: POST /api/users/{id}/reset-password (generates temp password, shown inline)
  - Self-service change: POST /api/auth/change-password (validates current, min 6 chars)
  - Settings page UI: "Change My Password" card + "Reset password" button per staff row
- **Session Idle Timeout** (Apr 2026):
  - 5-minute client-side idle timer tracking mouse/keyboard/touch/scroll
  - Auto-logout with "Session expired" toast on inactivity
  - 401 response interceptor clears auth state and redirects to login
- **PWA Wrapper** (Apr 2026):
  - manifest.json with standalone display, #243e36 theme
  - SVG icon (shield + checkmark)
  - Apple mobile web app meta tags for "Add to Home Screen"

## Backlog
- **P2**: Owner random sampling filters and variance drilldowns
- **Backlog**: AI-assisted scoring and automated quality checks

# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew**: Mobile field workers submitting photos via QR/link (no login)
- **Management** (Supervisor, PM, AM, GM): Reviews submissions, manages standards
- **Owner**: Final calibration, dataset approval, system oversight, reviewer analytics

## Core Requirements
- Mobile-first crew portal with division-aware tasking, OSHA incident/damage split, equipment logs
- High-accuracy GPS capture (+/-2m target, soft-warn + flag)
- Admin/Management/Owner dashboards with role-based visibility
- Tinder-style Rapid Review for fast mobile QA
- Supabase Object Storage for images
- JWT auth with lowercase email standardization
- Role-specific onboarding (Welcome Modal, Getting Started Panel, Help Popovers)
- 6 color themes + 4 font packages (independent of each other)
- Reviewer Performance Dashboard (owner-only)
- Closed-loop coaching from repeat-offender thresholds

## Tech Stack
- **Frontend**: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI + Motor (async MongoDB) + JWT Auth
- **Storage**: Supabase Storage (service role)
- **Database**: MongoDB

## Architecture
```
/app/backend/
  server.py, /shared/deps.py, /shared/models.py
  /routes/ (19 modules): auth, system, public, submissions, equipment,
    jobs, crew_access, users, notifications, rubrics, standards,
    reviews, rapid_reviews, training, analytics, exports,
    integrations, reviewer_performance, coaching
/app/frontend/src/
  /pages/ (12 pages), /components/common/, /components/theme/,
  /components/layout/, /components/ui/
```

## What's Been Implemented
- Full crew submission portal, standard/rapid review flows
- Standards library, repeat offender tracking, training mode, equipment logs
- Dynamic rubric matrix management, calibration heatmap, dataset exports
- Supabase image storage, backend modularization (19 route files)
- Role-specific onboarding UI
- **6 Color Themes**: Default, Dark, Tomboy, Gold, Noir, Neon — with 20+ CSS custom properties per theme + Tailwind variable overrides
- **4 Font Packages** (Apr 2026):
  - Brand (Cabinet Grotesk + Manrope — default)
  - Duckfake (Permanent Marker — grungy hand-painted)
  - Kid-Ergarten (Patrick Hand — childlike handwriting)
  - Hikaru (Fredoka — chunky cute rounded)
  - Independent of color theme, stored in separate localStorage key
  - Font picker on Settings page with live 'Aa' sample previews
- **Reviewer Performance Dashboard**: Owner-only, per-reviewer stats, speed trends, calibration drift
- **Closed-Loop Coaching**: Auto-generate training for Warning/Critical crews

## Backlog
- **P2**: Owner random sampling filters and variance drilldowns
- **Backlog**: Staff password reset/invite flows
- **Backlog**: AI-assisted scoring and automated quality checks

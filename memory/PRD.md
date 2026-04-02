# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew**: Mobile field workers submitting photos via QR/link (no login)
- **Management** (Supervisor, PM, AM, GM): Reviews, manages standards, coaching
- **Owner**: Calibration, dataset approval, system oversight, reviewer analytics, random sampling

## Tech Stack
- Frontend: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- Backend: FastAPI + Motor (async MongoDB) + JWT Auth
- Storage: Supabase Storage (service role)
- Database: MongoDB

## Architecture
```
/app/backend/
  server.py, auth_utils.py, /shared/deps.py, /shared/models.py
  /routes/ (19 modules): auth, system, public, submissions, equipment,
    jobs, crew_access, users, notifications, rubrics, standards,
    reviews, rapid_reviews, training, analytics, exports,
    integrations, reviewer_performance, coaching
/app/frontend/src/
  /pages/ (12 pages), /hooks/useIdleTimeout.js
  /components/common/, /components/theme/, /components/layout/, /components/ui/
  /public/ manifest.json, icon.svg
```

## Implemented Features
- Crew submission portal (work_date, incident/damage split, GPS accuracy polling)
- Standard + rapid review flows, standards library, repeat offender tracking
- Training mode, equipment maintenance logs, dynamic rubric matrices
- Calibration heatmap, dataset exports (CSV/JSONL), Supabase image storage
- Backend modularization (19 route files), role-specific onboarding UI
- 6 Color Themes + 4 Font Packages (independent, localStorage-persisted)
- Reviewer Performance Dashboard (owner-only, speed/drift/rating)
- Closed-Loop Coaching (auto-generate training for Warning/Critical crews)
- Staff password management (admin reset to temp + self-service change)
- 5-minute idle timeout + 401 interceptor, PWA manifest/meta tags
- **Owner Random Sampling** (Apr 2026):
  - Draw random subsets of submissions for spot-check review
  - Filter by crew, division, service type; configurable sample size (5-50)
  - Results table with color-coded variance (red/yellow/green)
  - Backend: GET /api/analytics/random-sample
- **Variance Drilldown** (Apr 2026):
  - Clickable heatmap cells expand to show individual submission-level details
  - Per-submission table: date, mgmt score, owner score, variance, rating, training status, issues
  - Sorted by largest variance for quick identification of calibration gaps
  - Backend: GET /api/analytics/variance-drilldown
- **AI-Assisted Scoring Placeholder** (Apr 2026):
  - Coming Soon card with Auto-grading, Anomaly Detection, Calibration Drift Alerts badges
  - Static placeholder — no backend logic yet

## Backlog
- **Backlog**: AI-assisted scoring backend implementation (when ready to integrate LLM)

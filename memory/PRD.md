# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
  - `server.py` (~120 lines) — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic
  - `shared/deps.py` — auth, helpers, Supabase
  - `routes/` — 20+ modular routers
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **Image Processing**: rembg (avatar background removal)
- **PDF Generation**: fpdf2

## Implemented Features

### V1.0–V1.4 (Prior Sessions)
- JWT auth, role-based routing, 8 themes (Default, Dark, Tomboy, Gold, Noir, Neon, Breakfast, Cafe)
- Photo submissions, Management & owner reviews, Equipment maintenance, Rapid Review
- Standards Library, Repeat Offenders, Training Mode
- Team Members (3 views), Avatar bg removal, Demo data seeding
- Metric widgets (Quality Trend, Standards Compliance, Training Funnel) with hover-to-expand

### V1.5 (Apr 4)
- Calibration page 500 bug fix, hover-to-expand metric cards, Breakfast + Cafe themes

### V1.6 (Apr 4)
- PM Dashboard, Crew Leader Performance, AM Client Report, Supervisor Checklist widgets
- Smart Insights bar, Sparklines on team cards, Weekly Digest

### V1.7 (Apr 4 — Current)
- **Server refactor**: `server.py` reduced from 819→120 lines. Seed data extracted to `shared/seed_data.py`. Dead files removed (`drive_sync.py`). 24 old test files cleaned.
- **PDF Export**: `/api/exports/am-report-pdf` generates downloadable PDF with property quality data, summary stats, and table. Export button on AM Report widget.
- **Onboarding Progress Tracker**: `/api/onboarding/progress` tracks 6 milestones per crew (first submission, first review, training started/completed, equipment check, 5 submissions). Widget shows progress bars and milestone badges.
- **Closed-Loop Coaching Reports**: `/api/coaching/loop-report` links repeat offenders→coaching actions→training sessions. CRUD for coaching actions (`assign`, `complete`). Widget shows summary stats + per-crew status (open/in_progress/closed).

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | JWT auth |
| GET | /api/exports/am-report-pdf | PDF download |
| GET | /api/onboarding/progress?division= | Crew onboarding milestones |
| GET | /api/coaching/loop-report?division= | Coaching completion status |
| POST | /api/coaching/assign | Assign coaching to crew |
| PATCH | /api/coaching/{id}/complete | Mark coaching done |
| GET | /api/metrics/pm-dashboard?division= | PM division snapshot |
| GET | /api/metrics/crew-leader-performance | Crew leader rankings |
| GET | /api/metrics/account-manager-report | Property quality report |
| GET | /api/metrics/supervisor-checklist | Daily equipment status |
| GET | /api/metrics/smart-insights | Auto-generated insights |
| GET | /api/metrics/crew-sparklines | 6-month sparklines |
| GET | /api/metrics/weekly-digest | Top/bottom performers |

## Pending / Backlog
- AI-assisted scoring backend (LLM integration)
- Quality Review Agent (pattern learning engine)

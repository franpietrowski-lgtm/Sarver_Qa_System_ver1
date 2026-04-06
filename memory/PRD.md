# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
  - `server.py` (~120 lines) — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic
  - `shared/deps.py` — auth, helpers, Supabase client
  - `routes/` — 23 modular routers
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **Image Processing**: rembg (avatar background removal)
- **PDF Generation**: fpdf2 (client reports with clickable image links)

## Implemented Features (V1.0–V1.8)

### Core System
- JWT auth, role-based routing (Owner, GM, PM, AM, Supervisor, Crew Leader, Crew Member)
- 8 workspace themes (Default, Dark, Tomboy, Gold, Noir, Neon, Breakfast, Cafe)
- Photo submissions with GPS, truck/division/task metadata
- Management & owner review workflows
- Rapid Review (Tinder-style swipe)
- Standards Library (19 industry standards)
- Repeat Offender Tracking
- Training Mode with quizzes
- Equipment maintenance logs with red-tag notifications

### Team & Analytics
- Team Members page (3 views: Hierarchy, Individual with sparklines, Table)
- Avatar background removal via rembg
- Division Quality Trend, Standards Compliance, Training Funnel (hover-to-expand, full-width row)
- PM Dashboard, Crew Leader Performance, Supervisor Checklist, Weekly Digest
- Smart Insights bar (auto-generated score alerts)

### V1.7 (Apr 4, 2026)
- **Server Refactor**: server.py 819→120 lines. Seed data → shared/seed_data.py. Dead files cleaned.
- **Full-Detail PDF Export**: Per-submission detail grouped by property. Includes crew notes, field/damage reports, GPS+time data, review scores, equipment logs. Clickable image links for all photos.
- **Onboarding Progress Tracker**: 6 milestones per crew. Widget with progress bars and milestone badges.
- **Closed-Loop Coaching Reports**: Links repeat offenders → coaching actions → training.

### V1.8 (Apr 6, 2026)
- **Standalone Client Quality Report Page** (`/client-report`): Dedicated page for Account Managers, GM, and Owner with job-specific search dropdown, timeframe cycling (Daily/Weekly/Monthly/Quarterly), executive summary table, per-property detail cards, and PDF export. Removed from Overview dashboard.
- **Overview Dashboard Cleanup**: AM Report widget removed. 3 metric cards (Division Quality Trend, Standards Compliance, Training Funnel) now span full row width. Coaching Loop widget hidden from Account Manager dashboard.
- **Crew Division Cascade**: When admin updates a crew QR link's division, all active crew members under that link automatically inherit the new division. Runtime sync also occurs when a crew member loads their dashboard.

## Key API Endpoints (23 route modules)
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/reports/job-search?q= | Fuzzy job search for Client Report |
| GET | /api/reports/client-quality?period=&job_id= | Client quality report data (JSON preview) |
| GET | /api/exports/am-report-pdf?period=&job_id= | Full-detail PDF with clickable photo links |
| GET | /api/onboarding/progress?division= | Crew onboarding milestones |
| GET | /api/coaching/loop-report?division= | Coaching completion loop |
| POST | /api/coaching/assign | Assign coaching action |
| PATCH | /api/coaching/{id}/complete | Complete coaching action |
| PATCH | /api/crew-access-links/{id} | Update crew link (cascades division to members) |
| GET | /api/public/crew-member/{code} | Get member (syncs division from parent) |
| GET | /api/metrics/* | 7 metric endpoints |
| GET | /api/analytics/* | Calibration/summary endpoints |

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request

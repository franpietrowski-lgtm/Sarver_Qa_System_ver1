# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
- **Database**: MongoDB (DB_NAME="test_database")
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **Image Processing**: rembg (avatar background removal)

## Implemented Features

### V1.0–V1.2 (Prior Sessions)
- JWT auth, role-based routing, dark/light theme (8 themes total)
- Photo submissions with GPS/truck/division/task
- Management & owner review workflows, equipment maintenance
- Rapid Review (Tinder-style swipe), Standards Library, Repeat Offenders, Training Mode
- CrewMember sub-system (QR registration), 30-day QR cleanup

### V1.3
- 19 real industry landscaping standards
- Team Members page (3 views), profile overlays with timeline stats
- Division switcher in crew app, leader_name field

### V1.4
- Division Hierarchy restructure: Owner->GM at top, AMs left, PMs right with crew arrows
- Profile overlay glass effect, Individual grid fix, Hover stats repositioned
- Avatar background removal (rembg), 3 demo crews, full demo dataset
- 3 metric endpoints (division-quality-trend, standards-compliance, training-funnel)
- Dark Mode hardcoded color sweep across all components

### V1.5 (Apr 4, 2026)
- **Bug Fix**: Analytics/Calibration page 500 errors — `KeyError: 'total_score'`
- **Hover-to-expand metric cards**: CSS grid-template-columns transition on 3 metric cards
- **Breakfast theme**: Warm waffle/chocolate/maple palette
- **Cafe theme**: Coffee/matcha/caramel palette

### V1.6 (Apr 4, 2026 — Current)
- **P1 Role-Specific Widgets:**
  - **PM Dashboard** — Division-scoped 90-day snapshot (subs, avg score, pass/fail, training). Shows only for Production Managers.
  - **Crew Leader Performance** — Ranked leader list with scores, progress bars. Shows for PMs (filtered by division) and Owner/GM (all).
  - **Account Manager Client Report** — Property quality table with submissions, avg score, pass/fail, divisions. Shows for AMs and Owner/GM.
  - **Supervisor Daily Checklist** — Today's equipment checks, submissions, active crews, red tags. Shows for Supervisors and Owner/GM.
- **P2 UX Improvements:**
  - **Smart Insights Bar** — Auto-generated score drop/rise alerts, training gap, red-tag counts. Shows contextual insight badges on Overview.
  - **Sparklines on Team Cards** — 6-month SVG sparklines on Individual view cards. PMs see division sparklines, others see aggregate.
  - **Weekly Digest Widget** — Top/bottom performing crews this week with score deltas.

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | JWT auth |
| GET | /api/metrics/pm-dashboard?division= | PM division snapshot |
| GET | /api/metrics/crew-leader-performance?division= | Crew leader rankings |
| GET | /api/metrics/account-manager-report | Property quality report |
| GET | /api/metrics/supervisor-checklist | Daily equipment/submission status |
| GET | /api/metrics/smart-insights | Auto-generated score insights |
| GET | /api/metrics/crew-sparklines?division= | 6-month sparklines (crew + division) |
| GET | /api/metrics/weekly-digest | Top/bottom performers |
| GET | /api/metrics/division-quality-trend | 30/60/90d rolling division scores |
| GET | /api/metrics/standards-compliance | Standard pass rates |
| GET | /api/metrics/training-funnel | Training completion funnel |
| GET | /api/analytics/summary | Calibration analytics |
| GET | /api/analytics/random-sample | Owner random sample tool |
| POST | /api/team/profiles/:id/avatar | Upload + bg removal |

## Pending / Backlog

### P2 — AI & Automation
- AI-assisted scoring backend (LLM integration for automated rubric grading)
- Closed-loop coaching completion reports
- Quality Review Agent (pattern learning engine)

### P2 — Enhancements
- Onboarding progress tracker for new crew members
- Score trend smart tooltips with specific crew/division context
- Exportable PDF reports from AM Client Report widget

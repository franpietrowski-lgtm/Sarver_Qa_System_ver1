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
- JWT auth, role-based routing, dark/light theme
- Photo submissions with GPS/truck/division/task
- Management & owner review workflows, equipment maintenance
- Rapid Review (Tinder-style swipe), Standards Library, Repeat Offenders, Training Mode
- CrewMember sub-system (QR registration), 30-day QR cleanup

### V1.3
- 19 real industry landscaping standards
- Team Members page (3 views), profile overlays with timeline stats
- Division switcher in crew app, leader_name field, QJA rename

### V1.4
- Division Hierarchy restructure: Owner->GM at top, AMs left, PMs right with crew arrows
- Profile overlay glass effect, Individual grid fix, Hover stats repositioned
- Avatar background removal (rembg), 3 demo crews, full demo dataset
- Workflow Guide, documentation updates
- 3 metric endpoints (division-quality-trend, standards-compliance, training-funnel)
- Dark Mode hardcoded color sweep across all components

### V1.5 (Current Session — Apr 4, 2026)
- **Bug Fix**: Analytics/Calibration page 500 errors — `KeyError: 'total_score'` in `analytics.py`. Fixed all score field references to handle both `total_score` (new reviews) and `overall_score` (seeded data) via `.get()` fallbacks.
- **Hover-to-expand metric cards**: Division Quality Trend, Standards Compliance, and Training Funnel cards on Overview page now expand on hover (CSS grid-template-columns transition: hovered card grows to 2.2fr, others shrink to 0.9fr). Each shows expanded detail panel (score breakdowns, passing/at-risk/failing counts, crews/members breakdown).
- Fixed rubric matrix card using hardcoded `bg-white/95` → `bg-[var(--card)]` for dark mode.

## Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | JWT auth |
| GET | /api/public/standards?division= | Standards by division |
| GET | /api/team/hierarchy | Org chart with PM-division mapping |
| GET | /api/team/profiles/:id/stats?months= | Timeline stats |
| POST | /api/team/profiles/:id/avatar | Upload + bg removal |
| GET | /api/analytics/summary | Calibration analytics (crew scores, heatmap) |
| GET | /api/analytics/random-sample | Owner random sample tool |
| GET | /api/analytics/variance-drilldown | Drill into crew/service variance |
| GET | /api/metrics/division-quality-trend | 30/60/90d rolling division scores |
| GET | /api/metrics/standards-compliance | Standard pass rates |
| GET | /api/metrics/training-funnel | Training completion funnel |

## Pending / Backlog

### P1 — Role-Specific Widgets
- PM Dashboard Widget: Division-scoped submission count + score trends
- Crew Leader Performance Card: Recent scores + training completion rate
- Account Manager Client Report: Exportable quality report per property
- Supervisor Daily Checklist: Equipment pre-check tracker

### P2 — UX Improvements
- Smart tooltips ("Crew avg score dropped 12% in 30 days")
- Score trend sparklines on team cards (90-day trajectory)
- Weekly digest widget (top/bottom performers)
- Onboarding progress tracker for new crew members

### P2 — AI & Automation
- AI-assisted scoring backend
- Closed-loop coaching completion reports
- Quality Review Agent (pattern learning engine)

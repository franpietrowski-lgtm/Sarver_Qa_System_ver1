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

### V1.3 (Previous Session)
- 19 real industry landscaping standards
- Team Members page (3 views), profile overlays with timeline stats
- Division switcher in crew app, leader_name field, QJA rename

### V1.4 (Current Session)
- **Division Hierarchy restructure**: Owner→GM at top, Account Managers on left connected to GM, Production Managers on right with direct arrows to their division crews. David Park tagged as Plant Healthcare.
- **Profile overlay glass effect**: backdrop-filter blur(20px) + bg-black/60, fully opaque card
- **Individual grid fix**: CSS grid for proper column alignment across all rows
- **Hover stats repositioned**: Tooltip appears above card (not below) to prevent row overlap
- **Avatar background removal**: rembg integration, outputs transparent PNG
- **3 demo crews**: Maintenance Alpha (3-man), Maintenance Bravo (4-man), Tree Alpha (4-man w/ PHC)
- **Full demo dataset**: 29+ submissions, 25+ reviews, 42 training sessions, 10 rapid reviews
- **Workflow Guide**: `/app/memory/WORKFLOW_GUIDE.md` with role access matrix and interaction training
- **Documentation updated**: README, frontend README, test_credentials

## Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | JWT auth |
| GET | /api/public/standards?division= | Standards by division |
| GET | /api/team/hierarchy | Org chart with PM-division mapping |
| GET | /api/team/profiles/:id/stats?months= | Timeline stats |
| POST | /api/team/profiles/:id/avatar | Upload + bg removal |

## Pending / Backlog

### P1 — Role-Specific Widgets
- PM Dashboard Widget: Division-scoped submission count + score trends
- Crew Leader Performance Card: Recent scores + training completion rate
- Account Manager Client Report: Exportable quality report per property
- Supervisor Daily Checklist: Equipment pre-check tracker

### P1 — Metric Tracking
- Standards Compliance Rate: % passing all checklist items
- Training Completion Funnel: Onboarding → standard viewed → quiz → pass
- Red-Tag Resolution Time: Equipment downtime tracking
- Division Quality Trend: Rolling 30/60/90 day average scores

### P2 — UX Improvements
- Smart tooltips ("Crew avg score dropped 12% in 30 days")
- Score trend sparklines on team cards (90-day trajectory)
- Weekly digest widget (top/bottom performers)
- Onboarding progress tracker for new crew members

### P2 — AI & Automation
- AI-assisted scoring backend
- Closed-loop coaching completion reports
- Quality Review Agent (pattern learning engine)

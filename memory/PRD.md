# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Owner/GM**: Strategic oversight, calibration, rubric management, export datasets
- **Management** (Production Managers, Account Managers, Supervisors): Review/score submissions, monitor crew quality
- **Crew Leaders**: Field photo capture, standards reference, division switching for cross-division work
- **Crew Members**: Register via QR, view assignments, access standards

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
- **Database**: MongoDB (DB_NAME="test_database")
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **Image Processing**: rembg (avatar background removal)

## Implemented Features

### V1.0 — Core System
- JWT auth with unified login, role-based routing
- Photo submissions with GPS, truck, division, task
- Management & owner review workflows
- Equipment maintenance with red-tag notifications
- Dark/light theme toggler

### V1.1 — QA Expansion
- Rapid Review (Tinder-style swipe)
- Standards Library (dynamic categories, CRUD)
- Repeat Offender tracking
- Training Mode (quiz-based)
- Pagination and optimization

### V1.2 — Crew & Team Management
- CrewMember sub-system (QR registration)
- Crew Leader "My Team" panel
- 30-day auto-cleanup for archived QR codes

### V1.3 — Standards & Org Chart
- 19 real industry landscaping standards
- Team Members page with 3 views
- Profile overlay with stats timeline (1/3/6/12/24mo)
- Division switcher in crew app
- leader_name field for crew access links
- QJA navigation rename

### V1.4 — Demo Data & System Health (Current Session)
- **3 new demo crews**: Maintenance Alpha (3-man), Maintenance Bravo (4-man), Tree Alpha (4-man with PHC specialist)
- **29+ submissions** with management reviews across all divisions
- **42 training sessions** at crew and individual level
- **10 rapid reviews** for swipe mode testing
- **Division Hierarchy fix**: Direct GM→PM paths, direct PM→team paths visible per division
- **Avatar background removal**: rembg integration with graceful fallback
- **Updated documentation**: README, frontend README, test_credentials

## Key Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | JWT auth |
| GET | /api/public/standards?division= | Standards by division |
| GET | /api/team/profiles | All profiles |
| GET | /api/team/hierarchy | Org chart with PM-division mapping |
| GET | /api/team/profiles/:id/stats?months= | Timeline stats |
| POST | /api/team/profiles/:id/avatar | Upload + bg removal |
| GET | /api/submissions | Submission queue |
| GET/POST | /api/rapid-review | Rapid review |

## DB Schema
- `users`: {email, hashed_password, role, active, name, division, title}
- `crew_access_links`: {code, label, leader_name, division, truck_number, enabled}
- `crew_members`: {code, name, parent_access_code, division, active}
- `standards_library`: {title, category, division_targets[], checklist[], notes, image_url, training_enabled}
- `submissions`, `management_reviews`, `owner_reviews`, `rapid_reviews`
- `training_sessions`, `equipment_logs`, `notifications`

## Pending / Backlog

### P1 — Role-Specific Enhancements (Recommended)
- **PM Dashboard Widget**: Submission count/score trends specific to PM's assigned division
- **Crew Leader Performance Card**: Quick view of their crew's recent scores, training completion rate
- **Account Manager Client Report**: Exportable quality report per property/client
- **Supervisor Daily Checklist**: Equipment pre-check completion tracker, crew coverage heatmap

### P1 — Metric Tracking Additions
- **Time-to-Review**: Track hours from submission to first review — surface bottlenecks
- **Division Quality Trend**: Rolling 30/60/90 day average scores per division
- **Standards Compliance Rate**: % of submissions that pass all checklist items per standard
- **Training Completion Funnel**: Track onboarding → first standard viewed → first quiz → first pass
- **Red-Tag Resolution Time**: Equipment downtime tracking from red-tag to resolution

### P2 — Actionable Improvements
- **Smart Tooltips**: Context-aware hints on hover (e.g., "This crew's avg score dropped 12% in the last 30 days")
- **Score Trend Sparklines**: Inline mini-charts on team cards showing 90-day score trajectory
- **Weekly Digest Widget**: Auto-generated summary of top/bottom performers, flagged submissions
- **Quick Actions Bar**: One-tap access to "Review Next", "Flag for Training", "Generate Report"
- **Onboarding Progress Tracker**: Visual checklist for new crew members (profile complete, standards viewed, first submission, first training)

### P2 — AI & Automation
- AI-assisted scoring backend
- Closed-loop coaching completion reports
- Quality Review Agent (pattern learning engine)

# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training. The system has expanded into a comprehensive QA System (V2.0) including Rapid Review with dynamic rubric grading matrices, Standards Library, Standalone Client PDF Reporting, Incident/Accident reporting workflows, and a Glass-morphic theme-compliant UI.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
  - `server.py` — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic
  - `shared/deps.py` — auth, helpers, Supabase client
  - `routes/` — 24+ modular routers (including `incidents.py`, `rapid_reviews.py`, `rubrics.py`)
  - `scripts/` — demo seed scripts (`demo_workflow_seed.py`, `demo_workflow_seed_phase2.py`)
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **PDF Generation**: fpdf2

## Implemented Features

### Core System (V1.0)
- JWT auth, role-based routing (Owner, GM, PM, AM, Supervisor, Crew Leader, Crew Member)
- 8 workspace themes (Default, Dark, Tomboy, Gold, Noir, Neon, Breakfast, Cafe) — all UI elements use CSS variables
- Photo submissions with GPS, truck/division/task metadata
- Management & owner review workflows
- Standards Library (19 industry standards)
- Repeat Offender Tracking
- Training Mode with quizzes
- Equipment maintenance logs with red-tag notifications

### V1.8 — Client Report, Division Cascade
- Standalone Client Quality Report page with glass dropdown, timeframe cycling, PDF export
- Crew division cascade on admin QR update

### V1.9 — Emergency Incidents
- Emergency incident/accident reporting (bypasses photo requirement)
- Overview alert widget with flash red, glass hover preview, click-to-open modal
- Incident acknowledgment/dismissal flow on dashboards
- 12 demo jobs (LMN-4201-4212) for search testing

### V2.0 (Apr 9, 2026) — Rubric Grading, Crew History, Glass UI
- Glass effect on ALL dropdowns with `glass-dropdown` CSS class
- Rapid Review rubric grading modal with click-to-autofill rubric hint chips
- Hard fail conditions (`no_image_captured`, `improper_image_quality`) on all 21 rubric definitions
- Crew QR App History Tab + Crew Leader member link integration
- Database curation with Longvue HOA demo jobs (LMN-5001-5005)
- Mobile responsive fixes and full theme compliance

### V2.1 (Apr 9, 2026) — Demo Workflow Seed
- End-to-end demo data: Account Manager job creation -> PM assignment -> Crew Leader 3-photo submission -> Crew Member 3-photo submission -> Emergency damage report -> 7-reviewer grading
- Job LMN-6001: "Longvue HOA - 291 Mailbox Bed Edging" with real field photos uploaded to Supabase
- 5 real user-provided field photos (bed edging, mulch work, dump truck) stored in Supabase
- 7 rapid reviews + 1 management review from diverse admin roles (excluding Owner, GM, and 3 others per user spec)
- Emergency incident with dump truck plant damage photo, visible on dashboard alert widget

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST   | /api/auth/login | JWT login |
| GET    | /api/rubrics | All rubric definitions |
| GET    | /api/rubrics/for-task?service_type=&division= | Task-specific rubric categories |
| GET    | /api/rapid-reviews/queue | Paginated queue of unreviewed submissions |
| POST   | /api/rapid-reviews | Submit rapid review with rubric scoring |
| PATCH  | /api/incidents/{id}/acknowledge | Mark emergency incident as read |
| GET    | /api/incidents/active | Active (unacknowledged) emergency incidents |
| GET    | /api/reports/job-search?q= | Fuzzy job search |
| GET    | /api/reports/client-quality?period=&job_id= | Client quality report JSON |
| POST   | /api/public/submissions | Create submission (photos optional for emergencies) |
| GET    | /api/public/crew-link/{code}/submissions | Crew submission history |
| GET    | /api/public/crew-submissions/{access_code} | Crew portal submission list |

## Key DB Schema
- `users`: {email, hashed_password, role, active, name, division, title}
- `crew_access_links`: {code, label, division, leader_name, truck_number, enabled}
- `jobs`: {job_id, job_name, property_name, address, service_type, division, truck_number, scheduled_date}
- `submissions`: {id, access_code, crew_label, job_id, photo_files[], field_report{}, is_emergency, status}
- `management_reviews`: {submission_id, reviewer_id, category_scores, total_score, disposition}
- `rapid_reviews`: {submission_id (unique), reviewer_id, overall_rating, rubric_sum_percent, comment}
- `rubric_definitions`: {service_type, categories[{label, weight, key, max_score}], hard_fail_conditions[]}
- `incidents`: queried via submissions with is_emergency=true
- `notifications`: {title, message, audience, status}

## Demo Data Summary
- 12 admin users across 5 role levels
- 6 crew QR links (Install Alpha, Maintenance Alpha/Bravo, Tree Alpha, Fran's Crew, Tim's Crew)
- 11+ submissions with real field photos from Supabase storage
- 21 rubric definitions with hard fail conditions
- Job LMN-6001 with full role-to-role workflow demonstration

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request
- Closed-loop coaching system (auto training from repeat-offender thresholds) — P2
- Refactoring: Extract large page components (`CrewCapturePage.jsx`, `OverviewPage.jsx`) into smaller widgets

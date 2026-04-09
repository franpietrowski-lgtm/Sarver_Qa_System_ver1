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
- **Glass effect on ALL dropdowns**: Client Report search, CrewCapturePage selects, CrewMemberDashboard selects, Settings page selects. All use `glass-dropdown` CSS class + `var(--accent)` backgrounds.
- **Rapid Review rubric grading modal**: Toggleable overlay shows task-specific rubric categories with names, weights, fail/exemplary clue indicators. Click-to-autofill rubric hint chips in comments. Hard fail conditions (`no_image_captured`, `improper_image_quality`) on all 21 rubric definitions.
- **Crew QR App History Tab**: Crew leaders can view submission history in a dedicated tab.
- **Crew Leader member link integration**: Team members can register via `/member/join/{parentCode}`.
- **Database curation**: Seeded real Longvue HOA jobs (LMN-5001–5005), retained "Fran" and "Tim" profiles, deleted photoless mock data.
- **Mobile responsive fixes**: Metrics widgets collapse to single column. Incident preview repositions. Overview grid stacks vertically.
- **Full theme compliance**: Settings page, theme cards, font cards fully converted to CSS variables. Compact 8-column theme cards, 4-column font cards.

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST   | /api/auth/login | JWT login |
| GET    | /api/rubrics | All rubric definitions |
| GET    | /api/rubrics/for-task?service_type=&division= | Task-specific rubric categories with fail/top indicators |
| GET    | /api/rapid-reviews/queue | Paginated queue of unreviewed submissions |
| POST   | /api/rapid-reviews | Submit rapid review with rubric scoring |
| PATCH  | /api/incidents/{id}/acknowledge | Mark emergency incident as read |
| GET    | /api/incidents/active | Active (unacknowledged) emergency incidents |
| GET    | /api/reports/job-search?q= | Fuzzy job search |
| GET    | /api/reports/client-quality?period=&job_id= | Client quality report JSON |
| GET    | /api/exports/am-report-pdf?period=&job_id= | PDF export |
| POST   | /api/public/submissions | Create submission (photos optional for emergencies) |
| GET    | /api/public/crew-link/{code}/submissions | Crew submission history |

## Key DB Schema
- `users`: {email, hashed_password, role, active, name, division}
- `crew_access_links`: {code, label, division, leader_name, truck_number, enabled}
- `jobs`, `submissions`, `management_reviews`, `owner_reviews`, `exports`
- `standards_library`: {title, category, rules, images}
- `training_sessions`: {crew_id, modules, score}
- `equipment_logs`: {equipment_number, pre_photo, post_photo, notes, red_tag}
- `notifications`: {user_id, message, read}
- `incidents`: {crew_id, submitter_type, notes, photos, acknowledged, timestamp}
- `rubric_definitions`: {service_type, title, categories[{label, weight, key}], hard_fail_conditions[], is_active, version}
- `rapid_reviews`: {submission_id, overall_rating, comments, rubric_scores, score_summary}

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request
- Closed-loop coaching system (auto training from repeat-offender thresholds) — P2
- Refactoring: Extract `CrewCapturePage.jsx` and `OverviewPage.jsx` widgets into `/components/`

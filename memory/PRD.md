# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training. The system has expanded into a comprehensive QA System (V2.2) with full theme compliance, Rapid Review with dynamic rubric grading, Daily Crew Assignments, Closed-Loop Coaching, Standards Library, Client PDF Reporting, Incident Reporting, and expandable Workflow Guides.

## Core Architecture
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI (modular routers in `/app/backend/routes/`)
  - `server.py` — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic
  - `shared/deps.py` — auth, helpers, Supabase client
  - `routes/` — 25+ modular routers (including `crew_assignments.py`, `coaching.py`, `incidents.py`)
  - `scripts/` — demo seed scripts (workflow, rubric expansion)
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **PDF**: fpdf2 (client reports + system reference)
- **Themes**: 8 themes (Default, Dark, Tomboy, Gold, Noir, Neon, Breakfast, Cafe) — all via CSS variables

## Implemented Features

### Core System (V1.0)
- JWT auth, role-based routing (Owner, GM, PM, AM, Supervisor, Crew Leader, Crew Member)
- 8 workspace themes — all UI elements use CSS variables exclusively (zero hardcoded colors)
- Photo submissions with GPS, truck/division/task metadata
- Management & owner review workflows with rubric scoring
- Standards Library (25 standards across 6+ categories)
- Repeat Offender Tracking
- Training Mode with quizzes
- Equipment maintenance logs with red-tag notifications

### V1.8 — Client Report, Division Cascade
- Standalone Client Quality Report with glass dropdown, timeframe cycling, PDF export
- Crew division cascade on admin QR update

### V1.9 — Emergency Incidents
- Emergency incident/accident reporting (bypasses photo requirement)
- Overview alert widget with flash-red animation, glass preview, click-to-open modal
- Incident acknowledgment/dismissal flow

### V2.0 — Rubric Grading, Crew History
- Rapid Review rubric grading modal with click-to-autofill rubric hint chips
- Hard fail conditions on all rubrics (no_image_captured, improper_image_quality)
- Crew QR App History Tab + Crew Leader member link
- Glass-morphic dropdowns application-wide

### V2.1 — Demo Workflow Seed
- End-to-end demo data: AM job creation → PM assignment → Crew submissions → Grading
- Job LMN-6001 with 5 real field photos in Supabase
- 7 reviewers with distributed rapid + management reviews

### V2.2 (Apr 9, 2026) — Theme Compliance, Crew Assignments, Coaching, Settings
- **Full theme compliance**: All `#243e36`/`#1a2c26` hardcoded colors replaced with `var(--btn-accent)`/`var(--btn-accent-hover)` across ALL pages and components. Zero hardcoded color references remain.
- **Review Queue theme fix**: Field report/damage card now uses `--status-critical-bg/border/text` variables. All form elements, badges, and cards use theme variables.
- **Rapid Review QR fix**: Always black-on-white (bgColor=#fff, fgColor=#000). Enlarged to 140px. Description below QR. Prominent Open + Copy Link buttons.
- **Daily Crew Assignment page** (`/crew-assignments`): Mon-Fri week grid with drag-drop job assignment. + button modal for manual assignment. Pre-load Week Forecast auto-assigns by division/truck matching. Delete assignments via trash icon. Job pool with search filter.
- **Rubric expansion**: 33 active rubrics across 7 divisions (added Enhancement: seasonal color, landscape design; Irrigation: repair, winterization, spring startup; Maintenance: aeration, overseeding, turf mowing; Install: retaining wall, paver patio; Tree: canopy lifting, cabling/bracing).
- **Standards expansion**: 25 standards (added irrigation repair, seasonal color, turf mowing, retaining wall, aeration, canopy lifting).
- **Score-based coaching analysis**: `/api/coaching/score-analysis` endpoint analyzes crew scores by task/rubric over 90-day window. Returns coaching priority (high/medium/low), weak tasks, and division summary.
- **Score-Based Coaching widget**: Overview dashboard widget showing crew performance with color-coded priority badges and weak task identification.
- **Settings overhaul**: Condensed architecture/tech/schema into downloadable System Reference PDF. Added expandable Workflow Guide cards (6 guides: Onboarding, Job/Crew Allocation, Rapid Review, Incident Reporting, Coaching Loop, Client Report).
- **Brand voice content**: Updated headings/descriptions across Overview ("Character, quality, respect — in every proof set"), Crew Portal ("Every proof set builds our reputation"), Review Queue ("Score every proof set with care"), Rapid Review completion ("Every proof set reviewed — quality holds").
- **Cleaned test rubric data**: Removed 9 leftover test entries from dev iterations.

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST   | /api/auth/login | JWT authentication |
| GET    | /api/rubrics | All 33 rubric definitions |
| GET    | /api/rapid-reviews/queue | Unreviewed submission queue |
| POST   | /api/rapid-reviews | Submit rapid review |
| GET    | /api/crew-assignments/week | Weekly crew assignment board |
| POST   | /api/crew-assignments | Create single assignment |
| POST   | /api/crew-assignments/bulk | Bulk assign (week forecast) |
| DELETE | /api/crew-assignments/{id} | Remove assignment |
| GET    | /api/coaching/score-analysis | Score-based coaching recommendations |
| GET    | /api/incidents/active | Active emergency incidents |
| GET    | /api/exports/system-reference-pdf | System reference PDF |
| GET    | /api/exports/am-report-pdf | Client report PDF |

## Key DB Schema
- `users`: {email, hashed_password, role, active, name, division, title}
- `crew_access_links`: {code, label, division, leader_name, truck_number}
- `jobs`: {job_id, job_name, property_name, address, service_type, division, truck_number}
- `submissions`: {id, access_code, crew_label, photo_files[], field_report{}, is_emergency, status}
- `management_reviews`: {submission_id, reviewer_id, category_scores, total_score, disposition}
- `rapid_reviews`: {submission_id (unique), reviewer_id, overall_rating, rubric_sum_percent}
- `rubric_definitions`: 33 active across 7 divisions with hard_fail_conditions[]
- `standards_library`: 25 standards organized by category
- `crew_assignments`: {crew_code, job_id, date, priority, status, assigned_by}
- `notifications`: {title, message, audience, status}

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request
- Component refactoring: Extract widgets from large page files into `/components/`

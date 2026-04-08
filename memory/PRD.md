# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
  - `server.py` (~140 lines) — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic (15 jobs)
  - `shared/deps.py` — auth, helpers, Supabase client
  - `routes/` — 24+ modular routers
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **PDF Generation**: fpdf2

## Implemented Features

### Core System
- JWT auth, role-based routing (Owner, GM, PM, AM, Supervisor, Crew Leader, Crew Member)
- 8 workspace themes (Default, Dark, Tomboy, Gold, Noir, Neon, Breakfast, Cafe) — all UI elements use CSS variables
- Photo submissions with GPS, truck/division/task metadata
- Management & owner review workflows
- Rapid Review (Tinder-style swipe) with task rubric reference panel
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
- 12 demo jobs (LMN-4201–4212) for search testing

### V2.0 (Apr 7, 2026) — Glass Dropdowns, Rubric Reference, Mobile, Theme Compliance
- **Glass effect on ALL dropdowns**: Client Report search, CrewCapturePage selects (task type, damage type, incident type, body part), CrewMemberDashboard selects, Settings page role/title selects. All use `glass-dropdown` CSS class + `var(--accent)` backgrounds.
- **Incident acknowledge/dismiss**: Clicking incident card opens full detail modal with "Mark as Read & Dismiss" button. Backend PATCH `/api/incidents/{id}/acknowledge` marks incident as read. Active incidents feed excludes acknowledged. When all dismissed, widget disappears and dashboard returns to normal.
- **Rapid Review rubric reference panel**: Toggleable overlay shows task-specific rubric categories with names, weights, fail/exemplary clue indicators from actual rubric definitions. When Fail or Top comment modal opens, dynamic rubric hint chips appear — clicking a hint auto-appends it to the comment field. Hard fail conditions included.
- **Mobile responsive fixes**: Metrics widgets row collapses to single column on mobile. Incident hover preview repositions below card on small screens. Overview grid stacks vertically.
- **Full theme compliance**: Settings page (theme cards, font cards, storage, architecture, staff management) fully converted from hardcoded green/white to CSS variables. Compact theme cards (8 across) and font cards (4 across) on desktop.
- **Settings page shrunk**: Theme swatches + label only (no description), 8 columns. Font cards show "Aa" + label only, 4 columns.

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/rubrics/for-task?service_type=&division= | Task-specific rubric categories with fail/top indicators |
| PATCH | /api/incidents/{id}/acknowledge | Mark emergency incident as read |
| GET | /api/incidents/active | Active (unacknowledged) emergency incidents |
| GET | /api/reports/job-search?q= | Fuzzy job search |
| GET | /api/reports/client-quality?period=&job_id= | Client quality report JSON |
| GET | /api/exports/am-report-pdf?period=&job_id= | PDF export |
| POST | /api/public/submissions | Create submission (photos optional for emergencies) |

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request

# Sarver Landscape QA System — Product Requirements

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Core Architecture
- **Frontend**: React + TailwindCSS + Shadcn UI + Framer Motion
- **Backend**: FastAPI (modular routes in `/app/backend/routes/`)
  - `server.py` (~138 lines) — app setup, startup, router registration
  - `shared/seed_data.py` — rubric library, default users, seed logic (15 jobs total)
  - `shared/deps.py` — auth, helpers, Supabase client
  - `routes/` — 24 modular routers (including incidents)
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **PDF Generation**: fpdf2

## Implemented Features (V1.0–V1.9)

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

### V1.7 — Server Refactor & Reporting
- Server refactor: server.py 819→120 lines
- Full-Detail PDF Export with clickable image links
- Onboarding Progress Tracker (6 milestones)
- Closed-Loop Coaching Reports

### V1.8 — Client Report Page & Division Cascade
- Standalone Client Quality Report page (`/client-report`) with job search, timeframe cycling, PDF export
- Overview cleanup: AM Report removed, full-width metrics, coaching loop hidden from AM
- Crew division cascade: admin QR updates propagate to all active crew members

### V1.9 (Apr 7, 2026) — Emergency Incidents & Search Enhancement
- **Client Report Dropdown Fix**: Dropdown only appears on ≥2 typed characters (no empty-focus populating). Glass backdrop-blur effect on dropdown. Shows "X matches found" header. Click-outside dismissal.
- **12 New Demo Jobs**: LMN-4201 through LMN-4212 covering spring cleanup, mulching, bed edging, pruning, weeding, property maintenance. Varied names (Birch Hill, Brighton Commons, Cedar Court, Cedar Point, Greenfield Plaza, Glen Meadow, Highland Ridge, Hilltop Gardens, Lakeshore Commons, Lakewood Estates, Oakridge Valley, Oak Summit) for search/sort testing.
- **Emergency Incident/Accident Reporting**: Crew Lead and Crew Member apps can file incident reports WITHOUT the 3-photo requirement. Submit button turns red with pulse animation when incident toggle is active. OSHA-compliant fields (incident type, date/time, location, injured person, body part, treatment, witness).
- **Emergency Broadcast Widget on Overview**: Flashing red card injected left of "Recent Submissions" when incidents exist. Hover shows glass popup with incident preview. Click opens full incident detail modal with all report fields.
- **Backend**: `/api/incidents/active` and `/api/incidents/{id}` endpoints. `is_emergency` flag on submissions. Photos made optional for emergency submissions. Emergency notifications broadcast to all admin roles including Owner.

## Key DB Schema Additions
- `submissions.is_emergency` — boolean flag for emergency incident submissions
- `submissions.field_report.type` — contains "Incident: ..." for emergency reports

## Key API Endpoints (24 route modules)
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/incidents/active | Active emergency incidents for Overview |
| GET | /api/incidents/{id} | Full incident detail |
| GET | /api/reports/job-search?q= | Fuzzy job search (min 2 chars recommended) |
| GET | /api/reports/client-quality?period=&job_id= | Client quality report JSON |
| GET | /api/exports/am-report-pdf?period=&job_id= | PDF export |
| POST | /api/public/submissions | Create submission (photos now optional for emergencies) |

## Pending / Backlog
- AI-assisted scoring backend (LLM integration) — ON HOLD per user request
- Quality Review Agent (pattern learning engine) — ON HOLD per user request

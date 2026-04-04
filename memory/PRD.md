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
- **Auth**: JWT-based, role-based routing

## Implemented Features (Production Ready)

### V1.0 — Core System
- JWT auth with unified login screen and role-based routing
- Crew capture portal (QR/link access, no login required)
- Photo submissions with GPS, truck, division, task type
- Management review workflow with rubric scoring
- Owner calibration review overlay
- Export pipeline for AI training datasets
- Equipment maintenance logging with red-tag notifications
- Dark/light theme toggler

### V1.1 — QA System Expansion
- Tinder-style "Rapid Review" swipe mode (strict mobile-first)
- Standards Library with dynamic categories, CRUD, edit/delete
- Repeat Offender tracking
- Training Mode with quiz-based sessions
- Pagination and DB query optimization

### V1.2 — Crew & Team Management
- CrewMember sub-system (QR registration, personal dashboard)
- Crew Leader "My Team" panel with member management
- 30-day auto-cleanup for archived QR codes
- Clipboard API fallback for iframe environments

### V1.3 — Team Members & Standards Overhaul (Current Session)
- **Team Members Page** with 3 views:
  - Individual: Responsive grid, hex avatars, role-colored accents, hover stats with 1/3/6/12/24 month timeline
  - Team Structure: Crew name header → leader → members, responsive card sizing
  - Division Hierarchy: Owner → GM → Production/Account Managers (cross-lateral) → Supervisors → Crews by division
- **Profile Overlay**: Centered enlarged view with avatar upload, stats toggle with timeline, quick links (Training, Heatmap, Repeat Offenders)
- **Industry Standards Library**: 19 real landscaping standards replacing test data:
  - Maintenance: Bed Edging, Spring/Fall Cleanup, Pruning, Mulching, Weeding
  - Install: Hardscape, Softscape, Lighting, Drainage
  - Tree: ISA Pruning, Tree Removal
  - Plant Healthcare: Chemical Application
  - Winter Services: Snow Removal
  - General: Safety, PPE, Photo Documentation, Equipment Pre-Check, Property Respect
- **Division Switcher in Crew App**: Crew leaders can switch divisions to access cross-division standards
- **leader_name field**: Crew access links now store the actual person's name (not just crew label)
- **QJA Navigation Rename**: "Alignment & QR" → "QJA"
- **DB Factory Reset**: Clean production-ready state (12 admins, 1 demo crew)

## Key API Endpoints
- `POST /api/auth/login` — JWT authentication
- `GET /api/public/standards?division=` — Division-filtered standards (no auth)
- `GET /api/team/profiles` — All team profiles
- `GET /api/team/structure` — Team structure with crews
- `GET /api/team/hierarchy` — Full org chart
- `GET /api/team/profiles/{id}/stats?months=` — Timeline performance stats
- `POST /api/team/profiles/{id}/avatar` — Avatar upload
- `POST /api/crew-access-links` — Create crew link (with leader_name)
- `GET /api/standards` — Standards library CRUD
- `POST /api/public/submissions` — Field submissions
- `GET/POST /api/rapid-review` — Rapid review queue

## DB Schema
- `users`: {email, hashed_password, role, active, name, division, title}
- `crew_access_links`: {code, label, leader_name, division, truck_number, enabled, archived}
- `crew_members`: {code, name, parent_access_code, active}
- `standards_library`: {title, category, division_targets[], checklist[], notes, image_url, training_enabled, question_*}
- `submissions`, `management_reviews`, `owner_reviews`, `rapid_reviews`
- `training_sessions`, `equipment_logs`, `notifications`

## Pending / Backlog
- P1: Avatar background removal (needs integration_playbook_expert_v2)
- P2: AI-assisted scoring (placeholder exists)
- P2: Closed-loop coaching completion reports
- Backlog: Quality Review Agent (pattern learning engine)

# Sarver Landscape — Quality Review System

A comprehensive field quality assurance platform for landscaping operations. Captures structured photo submissions from field crews, enables management to review and score work against industry-standard rubrics, and outputs structured datasets for AI training.

## Architecture

```
Frontend (React + TailwindCSS + Shadcn UI)
    ↕ REST API (REACT_APP_BACKEND_URL)
Backend (FastAPI + Motor/MongoDB)
    ↕ Storage
Supabase Object Storage (Images, Avatars)
```

## Quick Start

### Prerequisites
- Node.js 18+, Python 3.11+, MongoDB
- Supabase project (for image storage)

### Backend
```bash
cd backend
pip install -r requirements.txt
# Configure .env (MONGO_URL, DB_NAME, SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET, JWT_SECRET)
python seed_standards.py   # Seed 19 industry standards
python seed_demo_data.py   # Create demo crews + data
# Backend runs via supervisor on port 8001
```

### Frontend
```bash
cd frontend
yarn install
# Configure .env (REACT_APP_BACKEND_URL)
yarn start  # Runs on port 3000
```

## Features

### Crew Portal (No Login Required)
- QR/link access for field crews
- Photo capture with GPS, truck, division, task type
- Division-aware standards library with real-time switching
- Equipment maintenance logging with red-tag notifications
- Crew member registration and personal dashboards

### Management Dashboard
- Submission queue with status tracking
- Rubric-based scoring and review workflow
- Rapid Review: Tinder-style swipe mode for fast QA processing
- Standards Library CRUD with 19 industry-standard entries
- Repeat offender tracking and coaching workflows

### Owner/GM Dashboard
- Calibration review overlay
- Division hierarchy org chart (Owner → GM → PMs → Crews)
- Team Members directory with 3 views (Individual, Team Structure, Division Hierarchy)
- Reviewer performance analytics
- Dataset export pipeline for AI training
- Rubric matrix management

### Team Members (Infographic Org Chart)
- **Individual View**: Responsive grid with hex avatars, on-hover stats with 1/3/6/12/24mo timeline
- **Team Structure**: Crew name → Leader → Members with responsive sizing
- **Division Hierarchy**: Full org chart with PM-to-team direct paths
- **Profile Overlay**: Centered enlarged view, avatar upload (with auto background removal), performance stats, quick links

## Roles

| Role | Access | Key Features |
|------|--------|--------------|
| Owner | Full | Calibration, exports, rubric management, team oversight |
| GM | Full minus exports | Cross-division visibility, calibration |
| Production Manager | Division-scoped | Review submissions, team management |
| Account Manager | Cross-lateral | Client-facing quality reporting |
| Supervisor | Field oversight | Review queue, standard enforcement |
| Crew Leader | Crew portal | Photo capture, standards, equipment, team mgmt |
| Crew Member | Personal dashboard | View assignments, training, personal standards |

## Demo Data

The system ships with realistic demo data for onboarding:
- **12 admin users** across all management roles
- **4 crews**: Install Alpha, Maintenance Alpha, Maintenance Bravo, Tree Alpha
- **9 crew members** with varying start dates
- **29+ submissions** with management reviews
- **42 training sessions** across divisions
- **19 industry standards** covering Maintenance, Install, Tree, PHC, Winter, and Safety

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/login | None | JWT authentication |
| GET | /api/public/standards?division= | None | Division-filtered standards |
| GET | /api/public/crew-access/:code | None | Crew link lookup |
| POST | /api/public/submissions | None | Field submission |
| GET | /api/team/profiles | JWT | All team profiles |
| GET | /api/team/structure | JWT | Team structure |
| GET | /api/team/hierarchy | JWT | Full org chart with PM-division mapping |
| GET | /api/team/profiles/:id/stats | JWT | Timeline performance stats |
| POST | /api/team/profiles/:id/avatar | JWT | Avatar upload (auto background removal) |
| GET | /api/standards | JWT | Standards library |
| GET | /api/submissions | JWT | Submission queue |
| GET/POST | /api/rapid-review | JWT | Rapid review queue |

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI, Framer Motion
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic
- **Database**: MongoDB
- **Storage**: Supabase Object Storage
- **Auth**: JWT with role-based routing
- **Image Processing**: rembg (background removal), Pillow

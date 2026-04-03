# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## User Personas
- **Crew Leader**: Mobile field leader submitting photos via QR/link (no login), managing crew submissions
- **Crew Member**: Field worker with limited dashboard (capture, standards, training) accessed via shared QR registration
- **Management** (Supervisor, PM, AM, GM): Reviews, manages standards, coaching
- **Owner**: Calibration, dataset approval, system oversight, reviewer analytics, random sampling

## Tech Stack
- Frontend: React 19 + TailwindCSS + Shadcn/UI + Framer Motion
- Backend: FastAPI + Motor (async MongoDB) + JWT Auth
- Storage: Supabase Storage (service role)
- Database: MongoDB

## Architecture
```
/app/backend/
  server.py, auth_utils.py, /shared/deps.py, /shared/models.py
  /routes/ (20 modules): auth, system, public, submissions, equipment,
    jobs, crew_access, users, notifications, rubrics, standards,
    reviews, rapid_reviews, training, analytics, exports,
    integrations, reviewer_performance, coaching, crew_members
/app/frontend/src/
  /pages/ (14 pages), /hooks/useIdleTimeout.js
  /components/common/, /components/theme/, /components/layout/, /components/ui/
  /public/ manifest.json, icon.svg
```

## Implemented Features
- Crew submission portal (work_date, incident/damage split, GPS accuracy polling)
- Standard + rapid review flows, standards library, repeat offender tracking
- Training mode, equipment maintenance logs, dynamic rubric matrices
- Calibration heatmap, dataset exports (CSV/JSONL), Supabase image storage
- Backend modularization (20 route files), role-specific onboarding UI
- 6 Color Themes + 4 Font Packages (independent, localStorage-persisted)
- Reviewer Performance Dashboard (owner-only, speed/drift/rating)
- Closed-Loop Coaching (auto-generate training for Warning/Critical crews)
- Staff password management (admin reset to temp + self-service change)
- 5-minute idle timeout + 401 interceptor, PWA manifest/meta tags
- Owner Random Sampling with variance drilldown
- AI-Assisted Scoring Placeholder (Coming Soon card)
- **CrewMember Role & Dashboard** (Apr 2026):
  - Self-registration via shared link (`/member/join/:parentCode`)
  - Name + division form → Personal QR code generation
  - Limited dashboard at `/member/:code` with 4 tabs:
    - Capture (simplified — no damage/incident/equipment reporting)
    - Standards (read-only, division-filtered from standards library)
    - Training (parent crew's training sessions)
    - History (individual submission tracking via member_code)

## Backlog
  - Crew leader invite card on CrewCapturePage with copy link button
  - Crew leader "My Team" panel — collapsible list of registered members with submission counts, training completion %, and quick-view links
  - Backend: `crew_members` collection, 6 public API endpoints
  - Submissions tagged with `member_code` for individual tracking

- **Standards Library Dynamic Categories & CRUD** (Apr 2026):
  - Replaced 5 hardcoded categories with 30 dynamic categories covering all landscaping division tasks
  - Added "+ Custom category" option — users type a custom name, which is saved and appears in future dropdowns
  - Added Edit and Delete buttons to standard detail popup (delete requires 2-click confirmation)
  - Backend: `GET /api/standard-categories` (dynamic merge of defaults + DB), `DELETE /api/standards/{id}`
  - Category filter also uses the dynamic list
- **Backlog**: AI-assisted scoring backend implementation (when ready to integrate LLM)
- **Backlog**: Coaching completion report (closes loop back to offender tracker)

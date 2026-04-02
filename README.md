# Sarver Landscape — Field Quality Capture & Review System

A comprehensive internal QA platform for a landscaping company. Crews submit structured photo evidence of completed work. Management and ownership review, score, and calibrate using rubric-based workflows. The system outputs structured datasets for AI model training.

---

## System Overview

| Layer | Stack |
|-------|-------|
| **Frontend** | React 19, TailwindCSS, Shadcn/UI, Framer Motion |
| **Backend** | FastAPI (Python), Motor (async MongoDB), JWT auth |
| **Database** | MongoDB |
| **Storage** | Supabase (service-role image storage) |

### Architecture

```
/backend/
  server.py                  App setup, seed data, router orchestration
  /shared/
    deps.py                  DB connection, auth helpers, shared utilities
    models.py                Pydantic request/response schemas
  /routes/                   17 modular route files (59 total endpoints)
    auth.py                  Login, current user
    system.py                Health check, system blueprint
    public.py                Crew portal (no auth required)
    submissions.py           Submission files, list, detail, match override
    equipment.py             Equipment logs, red-tag forwarding
    jobs.py                  Job list, CSV import
    crew_access.py           Crew QR link CRUD
    users.py                 Staff account management
    notifications.py         Notification feed
    rubrics.py               Rubric matrix CRUD
    standards.py             Standards library CRUD
    reviews.py               Management + Owner review submission
    rapid_reviews.py         Rapid review swipe, sessions, flagged, rescore
    training.py              Training sessions, repeat offenders
    analytics.py             Dashboard overview, analytics summary
    exports.py               Dataset export (CSV/JSONL)
    integrations.py          Storage status, legacy drive endpoints

/frontend/
  /src/pages/                Role-aware page components
  /src/components/common/    Shared UI (HelpPopover, WelcomeModal, GettingStartedPanel)
  /src/components/ui/        Shadcn/UI primitives
  /src/lib/api.js            API client utilities
```

---

## Roles & Permissions

| Role | Titles | Access |
|------|--------|--------|
| **Crew** | — | Mobile capture portal via QR link (no login) |
| **Management** | Supervisor, Production Manager, Account Manager | Review queue, rapid review, standards, crew QR management |
| **Management** | GM (General Manager) | All management + rubric editing, equipment red-tag forwarding |
| **Owner** | Owner | All above + calibration, analytics, exports, rubric creation |

---

## Workflow Guide by Role

### Crew (No Login Required)

1. **Scan QR code** — opens the mobile capture portal for your assigned truck/division.
2. **Select or enter a job name** — jobs are pre-loaded if an admin imported a CSV schedule.
3. **Wait for GPS lock** — the system polls for ±2m accuracy over 10 seconds. A green "Precise" badge means you're good. If accuracy is >2m, the submission is still accepted but flagged for reviewer attention.
4. **Take photos** — minimum 3 per job (varies by rubric). Include one wide establishing shot, one detail, and one street-facing finish.
5. **Set work date and area tag** — helps management sort and track work.
6. **Report incidents/damage** (if any) — use the Incident/Damage tab for OSHA-compliant reporting with photos.
7. **Log equipment maintenance** — submit pre/post photos. Red-tag notes trigger escalation to PM and GM.
8. **Submit** — management is notified immediately.

### Management (Supervisor, PM, AM)

1. **Review submissions** — navigate to the review page. Score each rubric category (1–5), add comments, set disposition (pass, pass with notes, correction required, insufficient evidence).
2. **Rapid review (mobile swipe)** — open the swipe lane from the dashboard QR code:
   - **Swipe right** → Standard pass
   - **Swipe left** → Fail (comment required)
   - **Swipe up** → Exemplary (comment required)
   - Reviews under 4 seconds are flagged as "fast-graded"
3. **Import jobs via CSV** — go to Jobs & Alignment. Upload a UTF-8 CSV with these columns:

   | Column | Required | Notes |
   |--------|----------|-------|
   | `job_id` | Yes | Unique identifier; duplicates update existing records |
   | `job_name` | Yes | Human-readable job name |
   | `property_name` | No | Defaults to job_name |
   | `address` | No | Property address |
   | `service_type` | Yes | Must match a rubric (e.g., "bed edging", "spring cleanup") |
   | `scheduled_date` | No | ISO format (YYYY-MM-DD); defaults to today |
   | `division` | No | Defaults to "General" |
   | `truck_number` | Yes | Links jobs to crew QR codes |
   | `route` | No | Route label for grouping |
   | `latitude` / `longitude` | No | For GPS match scoring |

4. **Manage crew QR links** — create codes tied to truck numbers and divisions. Print and laminate for truck dashboards.
5. **Build standards** — create visual quality benchmarks with checklists. Toggle "Training enabled" to include in crew quiz sessions.

### GM (General Manager)

Everything above, plus:

1. **Edit rubric matrices** — create or tune grading rubrics per service type and division.
   - Each rubric has **categories** (grading factors) with weights summing to 1.0
   - Set **pass threshold** (minimum score % to pass)
   - Define **hard-fail conditions** (auto-fail regardless of score)
   - Set **min photos** required per submission
2. **Forward equipment red-tags** — escalate flagged equipment issues to the Owner for final review.
3. **Monitor repeat offenders** — view the heatmap of crews with recurring issues across 30/90/240-day windows.

### Owner

Everything above, plus:

1. **Calibrate scores** — your review follows management's first pass. The system tracks variance to surface calibration drift.
2. **Launch training sessions** — assign quiz sessions to specific crews from the Standards Library.
3. **Export datasets** — generate CSV or JSONL bundles. "Owner Gold" exports only owner-approved records for AI model training.
4. **Analytics dashboard** — view crew score trends, submission volume, calibration heatmaps, and fail-reason frequency by period (weekly/monthly/quarterly/yearly).

---

## Rubric Matrix Reference

Each service type has a rubric with weighted grading categories:

| Division | Service Types |
|----------|--------------|
| Maintenance | Bed Edging, Spring Cleanup, Fall Cleanup, Property Maintenance, Pruning, Weeding, Mulching |
| Install | Softscape, Hardscape, Tree/Plant Install/Removal, Drainage/Trenching, Lighting |
| Tree | Removal, Stump Grinding |
| Plant Healthcare | Fert & Chem Treatments, Air Spade, Dormant Pruning, Deer Fencing & Shrub Treatment |
| Winter Services | Snow Removal, Plow, Salting |

**Rubric structure:**
- **Categories**: 3–5 grading factors per rubric, each with a weight (decimal, must sum to 1.0) and max score of 5
- **Pass threshold**: Minimum combined score % to pass (typically 78–85%)
- **Hard-fail conditions**: Specific issues that cause automatic failure (e.g., "property_damage", "unsafe_debris_left_behind")
- **Versioning**: Creating a new rubric auto-increments the version. Old rubrics are deactivated, not deleted.

---

## In-App Guidance

The app includes built-in onboarding and contextual help:

- **Welcome Modal** — appears on first login with a role-specific step-by-step walkthrough (dismissible, stored per user)
- **Getting Started Panel** — persistent collapsible guide at the top of the dashboard with numbered tips (dismissible, can be re-shown by clearing browser storage)
- **Help Popovers** — clickable `?` icons next to key actions that expand into rich mini-guides with formatting rules, examples, and workflow instructions. Located on:
  - Overview dashboard (rubric matrix reference, rapid review controls)
  - Jobs & Alignment (CSV import format specification)
  - Crew QR management (link setup guide)
  - Rubric Editor (weights, thresholds, versioning)
  - Standards Library (authoring tips, training mode workflow)
  - Crew Capture portal (submission workflow, GPS tips)
  - Analytics (calibration heatmap reading guide)
  - Repeat Offenders (threshold tiers, training creation)

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Supabase account (for image storage)

### Backend
```bash
cd backend
pip install -r requirements.txt
# Configure .env with MONGO_URL, DB_NAME, JWT_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_BUCKET
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Frontend
```bash
cd frontend
yarn install
# Configure .env with REACT_APP_BACKEND_URL
yarn start
```

### Seed Data
On first startup, the backend automatically seeds:
- 12 staff accounts (Supervisors, PMs, AMs, GM, Owner)
- 21 rubric definitions across 5 divisions
- 3 crew QR access links
- 3 seed jobs
- 23 sample submissions with reviews and rapid reviews
- 4 standards library items

Default password for all seeded accounts: `SLMCo2026!`

---

## API Quick Reference

All endpoints are prefixed with `/api`. Authentication uses Bearer JWT tokens.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | No | Login with email + password |
| GET | `/auth/me` | Yes | Current user profile |
| GET | `/health` | No | Health check |
| GET | `/public/crew-access` | No | List active crew QR links |
| POST | `/public/submissions` | No | Create crew submission (multipart) |
| POST | `/public/equipment-logs` | No | Create equipment log (multipart) |
| GET | `/submissions` | Yes | Paginated submission list |
| GET | `/submissions/{id}` | Yes | Submission detail with snapshot |
| POST | `/submissions/{id}/match` | Yes | Override job match |
| GET | `/jobs` | Yes | Paginated job list |
| POST | `/jobs/import-csv` | Yes | Import jobs from CSV |
| GET | `/crew-access-links` | Yes | Paginated crew link list |
| POST | `/crew-access-links` | Yes | Create crew QR link |
| GET | `/rubrics` | Yes | Active rubric list |
| GET | `/rubric-matrices` | Yes | Filtered rubric matrix list |
| POST | `/rubric-matrices` | Yes | Create rubric matrix |
| GET | `/standards` | Yes | Paginated standards library |
| POST | `/standards` | Yes | Create standard item |
| POST | `/reviews/management` | Yes | Submit management review |
| POST | `/reviews/owner` | Owner | Submit owner review |
| GET | `/rapid-reviews/queue` | Yes | Rapid review queue |
| POST | `/rapid-reviews` | Yes | Submit rapid review |
| GET | `/repeat-offenders` | Yes | Repeat offender summary |
| GET | `/training-sessions` | Yes | Training session list |
| POST | `/training-sessions` | Yes | Create training session |
| GET | `/analytics/summary` | Yes | Analytics with calibration heatmap |
| POST | `/exports/run` | Yes | Generate dataset export |
| GET | `/dashboard/overview` | Yes | Dashboard stats |

---

## License

Internal use only — Sarver Landscape.

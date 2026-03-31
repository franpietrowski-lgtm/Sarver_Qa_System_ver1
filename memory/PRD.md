# PRD — Field Quality Capture & Review System

_Date updated: 2026-03-30_

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company that captures field work via structured photo submissions, links submissions to imported LMN job data, lets management review and score work with service rubrics, lets the owner finalize and calibrate scores, and outputs structured datasets for AI training and analytics. The system must support: no-login crew capture, management and owner dashboards, CSV/API-ready job import, auto-match suggestions, rubric versioning, Google Drive folder sync, JSONL/CSV exports, analytics, audit history, and workflow states from Draft through Exported.

## User Choices
- Authentication: email/password now, Google later
- Job import: CSV first, API-ready structure
- Photo storage: app storage + Google Drive sync architecture now
- Crew access: unique user QR code
- Scope priority: as much of the full spec as possible
- Admin account titles: GM, Account Manager, Production Manager, Supervisor (same review access)
- Reviewer calibration: owner-only function
- Crew data entry: free-text Job Name only for field input; align to imported job data later
- Crew field reporting: issues, damages, and notes with photo attachments
- Issue notifications: notify Production Managers + Account Managers first

## Architecture Decisions
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload handling
- Database: MongoDB collections with app-managed string IDs (avoids ObjectId leakage in API responses)
- Storage: local upload cache for fast proof capture, export files on server, Google Drive OAuth sync service layer prepared
- Access model: public QR crew routes, protected management/owner routes with role-aware navigation
- Review model: versioned rubric definitions stored in DB and applied by service type
- Job alignment model: crews submit only the job name they were given; admin users align records to imported job data separately

## User Personas
- Crew: mobile-first, no-login, rapid capture, minimal typing, field issue reporting
- Management/Admin: GM, Account Manager, Production Manager, Supervisor with shared review permissions
- Owner: calibration authority, resolves variance, approves training inclusion, drives export quality

## Core Requirements
- Crew submission with free-text job name, photos, truck number, GPS, timestamp, metadata
- Crew issue/damage/note intake with optional issue photo attachments
- CSV LMN-style job import and searchable job list
- Auto-match confidence and match status support for admin-side alignment
- Management scoring workflow with disposition and comments
- Owner-only calibration workflow with training inclusion/exclusion
- Versioned rubrics for bed edging, spring cleanup, fall cleanup
- JSONL/CSV exports for full and owner-gold datasets
- Analytics for crew scores, variance, fail reasons, and volume trends
- Audit history and relational linking across records

## What’s Implemented
### 2026-03-30
- Built public crew capture portal with QR-based access, job search, GPS capture, multi-photo upload, duplicate prevention, and review-ready submission creation
- Built JWT-based management/owner login with seeded demo accounts and role-based navigation
- Built job import + QR management workspace with CSV upload, active crew link generation, and printable QR cards
- Built management review queue with submission detail, match override, rubric scoring, flagged issues, and disposition handling
- Built owner calibration page with variance-aware scoring, final disposition, and training inclusion controls
- Built exports workspace supporting full dataset and owner-gold dataset generation in JSONL/CSV
- Built analytics dashboard for score-by-crew, variance, fail reasons, and submission volume trends
- Built system settings/blueprint page showing architecture, schema, workflow, stack, and Google Drive integration status
- Added backend support for local file persistence, JSON review artifacts, export records, audit history, and Google Drive OAuth sync scaffolding
- Fixed auth validation issue for seeded demo accounts and fixed Mongo ObjectId response leakage
- Fixed export workflow regression so dataset generation no longer empties active review queues
- Fixed authenticated export downloads in the frontend
- Added in-app notification center for management/owner review activity
- Added crew-facing follow-up notifications on the QR access portal when more photos are requested
- Added notification generation rules for new submissions, owner-review-ready items, and correction requests
- Added calibration heatmap analytics to surface grading variance by crew and service type
- Added learning roadmap / AI-readiness messaging so the current labeled dataset can evolve into future automated grading
- Updated admin model to GM / Account Manager / Production Manager / Supervisor plus Owner
- Updated crew capture to use free-text Job Name instead of requiring job selection from imported data
- Added field issue / damage / note reporting with attached issue photos into the review pipeline
- Updated notifications so field issues route first to Production Managers and Account Managers
- Updated the app styling direction to align more closely with Sarver Landscape branding cues
- Reworked owner analytics visuals to lightweight CSS-based charts for a cleaner testable experience
- Added crew link lifecycle controls so inactive QR links can be removed from active use without affecting prior submission history
- Added staff account management with create + authorize/deactivate controls for implementation testing
- Added owner queue pagination and a visible calibration heatmap legend
- Updated alignment views to hide truck display and reflect Sarver division structure: Maintenance, Install, PHC - Plant Healthcare, and Sarver Tree

## Prioritized Backlog
### P0
- Activate live Google Drive OAuth connection with user-provided Google client credentials
- Optionally add owner-specific live retest after real Google Drive credentials are connected

### P1
- Add LMN direct API sync after CSV-first workflow is validated
- Add richer job auto-match using imported coordinates and better route/time proximity rules
- Add rubric version management UI (create new versions, activate/deactivate, threshold editing)
- Add owner random sampling/high-value filters and variance drilldowns
- Add AI-assisted score suggestion mode that recommends likely rubric scores before human confirmation

### P2
- Add stronger offline tolerance for field crews
- Add granular audit viewer and reviewer activity history
- Add bulk export filters and scheduled export jobs
- Add Google social login as a second admin auth method

## Next Tasks List
- Connect live Google Drive credentials and validate folder/file sync end-to-end
- Expand seeded/sample data or import a real CSV to mirror production routing
- Add deeper calibration analytics by reviewer and service type
- Add editable admin settings for rubric thresholds and hard-fail conditions
- Plan the first AI grading assistant phase using the stored gold dataset + variance history
- Add staff password reset / invite flows for smoother production rollout

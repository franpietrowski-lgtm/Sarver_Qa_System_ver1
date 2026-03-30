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

## Architecture Decisions
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Recharts + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload handling
- Database: MongoDB collections with app-managed string IDs (avoids ObjectId leakage in API responses)
- Storage: local upload cache for fast proof capture, export files on server, Google Drive OAuth sync service layer prepared
- Access model: public QR crew routes, protected management/owner routes with role-aware navigation
- Review model: versioned rubric definitions stored in DB and applied by service type

## User Personas
- Crew: mobile-first, no-login, rapid capture, minimal typing
- Management: review queue operator, confirms matches, scores against rubric, flags issues
- Owner: calibration authority, resolves variance, approves training inclusion, drives export quality

## Core Requirements
- Crew submission with photos, job selection, truck number, GPS, timestamp, metadata
- CSV LMN-style job import and searchable job list
- Auto-match confidence and match status support
- Management scoring workflow with disposition and comments
- Owner calibration workflow with training inclusion/exclusion
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

## Prioritized Backlog
### P0
- Activate live Google Drive OAuth connection with user-provided Google client credentials
- Optionally add owner-specific live retest after real Google Drive credentials are connected

### P1
- Add LMN direct API sync after CSV-first workflow is validated
- Add richer job auto-match using imported coordinates and better route/time proximity rules
- Add rubric version management UI (create new versions, activate/deactivate, threshold editing)
- Add owner random sampling/high-value filters and variance drilldowns

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

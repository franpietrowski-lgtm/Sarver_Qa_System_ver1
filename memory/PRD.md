# PRD — Field Quality Capture & Review System

_Date updated: 2026-04-01_

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company that captures field work via structured photo submissions, links submissions to imported LMN job data, lets management review and score work with service rubrics, lets the owner finalize and calibrate scores, and outputs structured datasets for AI training and analytics. The system must support: no-login crew capture, management and owner dashboards, CSV/API-ready job import, auto-match suggestions, rubric versioning, Supabase-backed image storage, JSONL/CSV exports, analytics, audit history, and workflow states from Draft through Exported.

## User Choices
- Authentication: email/password now, Google later
- Job import: CSV first, API-ready structure
- Photo storage: Supabase Storage via backend-managed service role
- Crew access: unique user QR code
- Scope priority: as much of the full spec as possible
- Admin account titles: GM, Account Manager, Production Manager, Supervisor (same review access)
- Reviewer calibration: owner-only function
- Crew data entry: free-text Job Name only for field input; align to imported job data later
- Crew field reporting: issues, damages, and notes with photo attachments
- Issue notifications: notify Production Managers + Account Managers first
- V1.1 phase order: start with rapid review, role restrictions, theme toggle, login UX
- Training access target: no-login unique crew/session links
- Crew portal: standards highlights should be openable by crews; incident/damage entry should sit behind a toggle
- Repeat offender thresholds: customizable later rather than fixed now
- Login UX: branded start screen with standard user/pass flow, forgot user/pass link, grass-motion visuals, and role-aware post-login workflow
- Rapid Review: admin-only feature for Supervisor, Production Manager, Account Manager, GM, and Owner; must support both desktop/admin lane and mobile-link lane
- Rapid Review scoring: 4 states (Fail, Concern, Standard, Exemplary); Fail/Exemplary require reviewer comments before commit
- Rapid Review refinement: mobile-only in practice, launched by QR/mobile link from admin dashboards
- Standards Library: start with universal categories and allow division-specific omissions/bundles
- Training Mode phase choice: build session + swipe/quiz flow first, then add deeper history later
- Dashboard priority: Quality + Training should be at the forefront regardless of admin role
- Notifications: incident/damage alerts go to all admin roles except Owner; equipment Red-Tag flow goes to PM + Supervisor + GM
- Crew equipment logging: separate crew-side tab with pre-service photo, post-photo, Equipment##, General note, Red-Tag Note
- Crew QR editing: any admin role should be able to update crew QR metadata from the dashboard

## Architecture Decisions
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload handling
- Database: MongoDB collections with app-managed string IDs (avoids ObjectId leakage)
- Storage: Supabase Storage for proof images, backend-served image routes
- Access model: public QR crew routes, protected management/owner routes with role-aware navigation
- Review model: versioned rubric definitions stored in DB and applied by service type

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
- Dynamic rubric matrices by division/task with CRUD management for GM/Owner
- JSONL/CSV exports for full and owner-gold datasets
- Analytics for crew scores, variance, fail reasons, and volume trends
- Audit history and relational linking across records

## What's Implemented

### Through 2026-03-31 (prior sessions)
- Full crew capture portal with QR access, multi-photo upload, GPS, Supabase Storage
- JWT auth with seeded demo accounts and role-based navigation
- Job import + QR management workspace
- Management review queue with rubric scoring
- Owner calibration page with variance-aware scoring
- Exports workspace (JSONL/CSV)
- Analytics dashboard with period tabs
- Standards Library, Repeat Offenders, Training Mode
- Equipment Maintenance logs with Red-Tag notification flow
- Rapid Review mobile swipe mode
- Unified login screen with Sarver branding
- Theme toggler (dark/light)
- Pagination and DB optimization for deployment readiness
- Supabase Storage migration (from Google Drive)

### 2026-04-01
- Added division field to all 21 seeded rubric definitions (Maintenance, Install, Tree, Plant Healthcare, Winter Services)
- Built Dynamic Rubric Matrix CRUD API: GET /api/rubric-matrices (with division/service_type filter), POST (create), PATCH (update), DELETE (soft-deactivate) — GM/Owner only
- Added Quick Matrix Ref table to the Overview dashboard showing all rubrics by division with grading factors, pass thresholds, and version numbers, with a division filter dropdown
- Replaced crew portal text tabs ("Work capture", "Standards highlights", "Equipment maintenance") with icon-only tabs (Camera, BookOpen, Wrench) to prevent mobile text overflow
- Rewrote Rapid Review page as a strict mobile-only interface: removed queue strip, side panel, bulk actions, and all scrollable content below the image; layout is now image + swipe HUD + 4 rating buttons + skip
- Fixed dark theme visibility: added targeted CSS for Shadcn dropdown/select components, input fields, borders, badges, and table rows in dark mode

## Prioritized Backlog
### P0
- None currently blocking

### P1
- Break `backend/server.py` into focused modules (auth, submissions, reviews, analytics, exports, integrations)
- Expand Standards Library with richer media editing, searchable internal/crew splits
- Expand Repeat Offender tracking with configurable thresholds UI
- Expand Crew Training Mode with historical performance dashboards
- Add search-assisted job matching UX for large imported job libraries
- Add rubric version management UI (create new versions, activate/deactivate, threshold editing)
- Persist rapid-review annotations/comments into richer audit artifacts
- Add owner random sampling/high-value filters and variance drilldowns

### P2
- AI-assisted scoring (recommend rubric scores before human confirmation)
- Automate quality checks and grading using gathered rubric dataset (AI training)
- Closed-loop coaching system (auto-generating monthly training sessions from repeat-offender thresholds)
- Add stronger offline tolerance for field crews
- Add granular audit viewer and reviewer activity history
- Add bulk export filters and scheduled export jobs
- Add Google social login as a second admin auth method

## Next Tasks List
- Expand Rapid Review with optional revisit/edit flows for summary ratings
- Add stronger admin workflow links between Standards Library, Repeat Offenders, and Training Mode
- Finalize role-optimized dashboard so each role sees highest-value actions first
- Add deeper calibration analytics by reviewer and service type
- Add editable admin settings for rubric thresholds and hard-fail conditions
- Plan the first AI grading assistant phase
- Add staff password reset / invite flows

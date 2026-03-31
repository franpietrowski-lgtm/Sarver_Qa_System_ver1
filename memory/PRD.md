# PRD — Field Quality Capture & Review System

_Date updated: 2026-03-31_

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
- Rapid Review scoring: 4 states (Fail, Concern, Standard, Exemplary); Fail/Exemplary require reviewer comments before commit; one swipe sets an overall rating first and detailed rubric categories can be edited later
- Rapid Review refinement: mobile-only in practice, launched by QR/mobile link from admin dashboards rather than a desktop nav workspace
- Standards Library: start with universal categories (edging, mulch, cleanup, pruning, damage prevention) and allow division-specific omissions/bundles
- Training Mode phase choice: build session + swipe/quiz flow first, then add deeper history later

## Architecture Decisions
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Framer Motion
- Backend: FastAPI + Motor + JWT auth + multipart upload handling
- Database: MongoDB collections with app-managed string IDs (avoids ObjectId leakage in API responses)
- Storage: Supabase Storage for proof images, backend-served image routes, local export files on server
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
- Built system settings/blueprint page showing architecture, schema, workflow, stack, and storage/integration status
- Added backend support for file persistence, JSON review artifacts, export records, and audit history
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

### 2026-03-31
- Replaced the in-progress Google Drive migration path with Supabase Storage-backed upload and retrieval for submission photos and issue photos
- Updated backend submission file metadata to store Supabase bucket/path references while preserving stable `/api/submissions/files/...` review URLs
- Cleaned backend env/storage status so Google Drive redirect config is retired and Supabase storage status is surfaced in the app
- Optimized production-sensitive list and overview endpoints to use paginated queries, projections, counts, and server-side filtering instead of loading full collections into memory
- Added paginated API contracts for submissions, jobs, crew access links, and exports with `{ items, pagination }` responses
- Added frontend pagination at 10 items/page for owner queue, archived crew links, export history, active crew links, review queue, and imported jobs table
- Added analytics period tabs (daily, weekly, monthly, quarterly, annual) with filtered backend summaries
- Polished the crew portal copy to remove technical/no-login language and replaced the raw crew ID display with a cleaner “Crew pass active” label
- Updated settings and overview messaging from Google Drive wording to Supabase storage wording
- Fixed the analytics chart key warning found during testing after period-tab switching
- Added Phase 1 V1.1 login/start screen redesign with Sarver branding, wobbling vector grass backdrop, role preset chips, forgot user/pass helper, and remembered last-role hint
- Added authenticated workspace theme toggle with persistent default/dark modes while keeping the login screen on its own fixed brand presentation
- Enforced role-based navigation and route restrictions so owners no longer see Alignment & QR or Review Queue, and non-owners no longer see Exports
- Added full-screen Rapid Review mode for owner/management with queue strip, bulk pass/fail controls, pass/fail/flag/skip actions, keyboard shortcuts, swipe-capable cards, issue tagging, and inline annotation drawing
- Added a crew-facing Standards Highlights tab and moved incident/damage reporting behind an explicit toggle to reduce accidental field entry
- Added a safe image placeholder fallback for missing storage files so rapid review no longer throws server errors for broken image payloads
- Refined Rapid Review into an admin-only summary-rating lane with dedicated desktop and mobile-link routes, 4 rating states (Fail, Concern, Standard, Exemplary), standardized rubric sums, and required comment modal for Fail/Exemplary actions
- Added backend `rapid_reviews` summary records and queue exclusion so already-qualified items drop out of the swipe lane while still exposing summary cards in standard Review and Owner Review detail screens
- Shifted Rapid Review to a mobile-only launch pattern: no desktop sidebar entry, QR launch card on Overview, `/rapid-review` redirect to `/rapid-review/mobile`, and translucent directional HUD arrows so swipe meaning is immediately visible on phone
- Built Standards Library authoring with search/filter, universal categories, division targets, training-ready question authoring, edit support, and recent training session history
- Built Repeat Offender tracking with a backend aggregation endpoint, crew/issue heatmap, escalation levels, related-submission lists, and one-click training session generation
- Built first-pass Crew Training Mode with unique no-login session links, image-first flow, swipe/tap into quiz, multiple-choice/free-text support, completion summary, and invalid/completed-session error states
- Improved backend API contracts for this phase: create endpoints now return 201 where appropriate, and standards updates support partial PATCH payloads

## Prioritized Backlog
### P0
- Re-run deployment health review now that Supabase storage and paginated DB queries are in place
- Monitor large-data performance with real production-scale submissions after deployment review

### P1
- Break `backend/server.py` into focused modules (auth, submissions, reviews, analytics, exports, integrations)
- Expand Standards Library with richer media editing, searchable internal/crew splits, and assignment controls directly from offender/calibration views
- Expand Repeat Offender tracking with configurable thresholds UI, deeper drilldowns, and stronger links into Training Mode history
- Expand Crew Training Mode with historical performance dashboards, monthly auto-session generation, and richer answer analytics
- Add dynamic QR metadata editing for vehicle/division/assignment while preserving historical records
- Add richer analytics drilldowns by reviewer/service type within the new time windows
- Add search-assisted job matching UX for large imported job libraries
- Add LMN direct API sync after CSV-first workflow is validated
- Add richer job auto-match using imported coordinates and better route/time proximity rules
- Add rubric version management UI (create new versions, activate/deactivate, threshold editing)
- Persist rapid-review annotations/comments into richer audit artifacts and support revisiting/editing summary ratings
- Add owner random sampling/high-value filters and variance drilldowns
- Add AI-assisted score suggestion mode that recommends likely rubric scores before human confirmation

### P2
- Add stronger offline tolerance for field crews
- Add granular audit viewer and reviewer activity history
- Add bulk export filters and scheduled export jobs
- Add Google social login as a second admin auth method

## Next Tasks List
- Run deployment readiness / health review again against the updated Supabase + paginated-query build
- Expand Rapid Review from Phase 1 into stronger queue filters, persistent annotations, and optional revisit/edit flows for summary ratings
- Add stronger admin workflow links between Standards Library, Repeat Offenders, and Training Mode (assign/reassign, archive, reopen session)
- Expand seeded/sample data or import a real CSV to mirror production routing and validate multi-page queues further
- Add deeper calibration analytics by reviewer and service type inside the new daily/weekly/monthly/quarterly/annual filters
- Add editable admin settings for rubric thresholds and hard-fail conditions
- Plan the first AI grading assistant phase using the stored gold dataset + variance history
- Add staff password reset / invite flows for smoother production rollout

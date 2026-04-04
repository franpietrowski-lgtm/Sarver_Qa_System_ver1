# Sarver Landscape QA System — PRD

## Original Problem Statement
Build a lightweight, scalable internal application for a landscaping company (Sarver Landscape) that captures field work via structured photo submissions, allows management to review/score work using defined rubrics, and outputs structured datasets for AI training.

## Tech Stack
React 19 + TailwindCSS + Shadcn/UI + Framer Motion | FastAPI + Motor (async MongoDB) + JWT Auth | Supabase Storage

## Architecture
```
/app/backend/
  server.py, /routes/ (21 modules), /shared/deps.py, /shared/models.py
/app/frontend/src/
  /pages/ (15 pages), /hooks/, /components/, /lib/
```

## Authorized Admin Accounts (login_data.txt)
- Adam S (Owner): sadam.owner@slmco.local
- Tyler C (GM): ctyler.gm@slmco.local
- Brad S (PM-Tree): sbrad.gm@slmco.local
- Scott K, Megan M, Daniel T (Account Managers)
- Tim A (PM-Maintenance), Zach O (PM-Install), Scott W (PM-Maintenance)
- Johnny H, Craig S, Fran P (Supervisors)
All passwords: SLMCo2026!

## Implemented Features
- Crew submission portal, standard + rapid review, standards library, repeat offender tracking
- Training mode, equipment maintenance, dynamic rubric matrices, calibration heatmap
- Dataset exports, Supabase image storage, role-specific onboarding
- 6 Color Themes + 4 Font Packages, PWA, 5-min idle timeout
- Reviewer Performance Dashboard, Closed-Loop Coaching (auto-generate training)
- Staff password reset, Owner Random Sampling + variance drilldown
- **CrewMember Role & Dashboard** — Self-registration via QR, limited capture/standards/training
- **Team Members Page** (Apr 2026):
  - 3×5 grid with pagination (Individual view)
  - Graphic org chart with colored cards and connector lines (Team Structure + Division Hierarchy)
  - Hexagonal avatar clips, avatar upload to Supabase storage
  - Profile detail overlay with Performance & Records stats toggle
- **Standards Library CRUD** — 30 dynamic categories + custom entry, edit/delete from detail popup
- **Account Cleanup** — Removed all non-listed accounts, updated Brad S→PM[Tree], Megan M, Daniel T
- **QR Archive System** — Archive with 30-day auto-delete + manual permanent delete, countdown display

## Backlog
- **Backlog**: AI-assisted scoring backend (when ready to integrate LLM)
- **Backlog**: Coaching completion report (closes loop to offender tracker)
- **Backlog**: Background removal for profile avatar uploads (needs external API)

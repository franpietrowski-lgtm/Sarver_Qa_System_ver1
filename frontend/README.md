# Frontend — Sarver Landscape Quality Review

React-based single-page application for the Sarver Landscape QA System.

## Stack
- React 18 with React Router
- TailwindCSS + Shadcn UI components (`/src/components/ui/`)
- Framer Motion (swipe mechanics, page transitions)
- Lucide React icons

## Directory Structure
```
src/
├── components/
│   ├── layout/
│   │   └── AppShell.jsx          # Sidebar navigation, role routing
│   └── ui/                        # Shadcn UI components
├── lib/
│   ├── api.js                     # API helpers (authGet, authPost, publicGet)
│   └── clipboard.js               # Clipboard fallback for iframe environments
├── pages/
│   ├── OverviewPage.jsx           # Main dashboard
│   ├── TeamMembersPage.jsx        # Org chart (3 views)
│   ├── CrewCapturePage.jsx        # Crew portal (capture, standards, equipment)
│   ├── CrewMemberDashboard.jsx    # Personal crew member view
│   ├── RapidReviewPage.jsx        # Tinder-style swipe review
│   ├── StandardsLibraryPage.jsx   # Standards CRUD
│   ├── JobsPage.jsx               # QJA: crew links, QR codes
│   ├── AnalyticsPage.jsx          # Calibration heatmap
│   └── ...
└── App.jsx                        # Route definitions
```

## Key Features
- **Role-based navigation**: Owner/GM see full nav; Management sees scoped views; Crew sees portal only
- **Division switcher**: Crew leaders can switch divisions to access cross-division standards
- **Profile overlays**: Click any team member for enlarged profile with stats + quick links
- **Hover stats**: Timeline-selectable (1/3/6/12/24 months) performance data on hover
- **Responsive cards**: Grid adapts to screen size; cards enlarge when fewer are displayed

## Environment
```
REACT_APP_BACKEND_URL=https://your-app.preview.emergentagent.com
```

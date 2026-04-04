# Sarver Landscape QA System — Role Workflow & Interaction Guide

This document defines what each account role can see, do, and access within the system.
Use this for onboarding new users and training on dashboard functionality.

---

## OWNER (Adam S)

### Pages Available
| Page | What You See | What You Do |
|------|-------------|-------------|
| **Overview** | Company-wide submission count, review velocity, pending queue | Monitor overall QA health at a glance |
| **Submissions** | All submissions from every division | Review, score, or escalate any submission |
| **Rapid Review** | Swipe queue of pending submissions | Pass/Fail/Exemplary — high-speed mobile review |
| **Standards Library** | All 19 industry standards | Create, edit, delete standards. Define training questions |
| **QJA** | All active crew QR links | Create new crews, assign leader names, manage divisions |
| **Team Members** | Full org chart — Individual, Team Structure, Division Hierarchy | View all profiles, upload avatars, check performance stats |
| **Analytics** | Calibration heatmap, reviewer performance | Monitor scoring consistency across reviewers |
| **Training Mode** | Training session results | Review crew training completion and scores |
| **Repeat Offenders** | Crews with recurring quality issues | Track patterns, assign coaching sessions |

### Key Observations
- Owner sees **everything**. Use the Division Hierarchy to understand reporting chains.
- The Analytics heatmap shows if reviewers are scoring consistently — use this to calibrate your management team.
- Quick-access Performance Stats: Click any team member → toggle "Performance & Records" → select timeline (1/3/6/12/24 months).

---

## GM (Tyler C)

### Pages Available
| Page | What You See | What You Do |
|------|-------------|-------------|
| **Overview** | Company-wide dashboard | Same as Owner — cross-division visibility |
| **Submissions** | All submissions | Review and score from any division |
| **Rapid Review** | Full swipe queue | Process reviews at speed |
| **Standards Library** | All standards | Manage standards and training content |
| **QJA** | All crew links | Manage crew assignments and QR codes |
| **Team Members** | Full org chart | View all profiles and performance |
| **Analytics** | Heatmap and reviewer stats | Monitor reviewer consistency |
| **Training Mode** | All training results | Track training across divisions |

### Key Observations
- GM has direct lines to all Production Managers. Use Division Hierarchy to see PM → Crew flow.
- GM can see Account Manager sidebar — these are your client-facing liaisons.

---

## PRODUCTION MANAGER (Tim A, Zach O, Scott W, Brad S)

### Pages Available
| Page | What You See | What You Do |
|------|-------------|-------------|
| **Overview** | Division-scoped submission count | Monitor your division's output |
| **Submissions** | Submissions from your assigned division | Review and score your crews' work |
| **Rapid Review** | Division-scoped swipe queue | Quick-process your division's submissions |
| **Standards Library** | Standards relevant to your division | Reference standards when reviewing |
| **QJA** | Crew links in your division | Manage your crews' QR codes |
| **Team Members** | All profiles (read-only stats) | Check your crews' performance |
| **Training Mode** | Training for your division | Monitor crew training progress |

### Key Observations
- You manage the crews that report to you. In Division Hierarchy, you'll see your name next to your division with arrows to your crews.
- Use timeline stats (hover any crew member card) to track 30-day, 90-day, or longer performance trends.
- Flag repeat issues → they'll appear in Repeat Offenders for leadership to review.

---

## ACCOUNT MANAGER (Megan M, Daniel T, Scott K)

### Pages Available
| Page | What You See | What You Do |
|------|-------------|-------------|
| **Overview** | Cross-division dashboard | Monitor quality across client properties |
| **Submissions** | All submissions | Review submissions related to your accounts |
| **Standards Library** | All standards | Reference quality standards for client reporting |
| **Team Members** | All profiles | Check crew performance for your accounts |

### Key Observations
- Account Managers communicate cross-laterally with Production Managers. In the hierarchy, you're on the left side connected to GM — PMs and their crews are on the right.
- Use Performance Stats on crew members to build quality reports for client presentations.
- Your primary role is quality assurance from the client perspective — flag issues early.

---

## SUPERVISOR (Johnny H, Craig S, Fran P)

### Pages Available
| Page | What You See | What You Do |
|------|-------------|-------------|
| **Overview** | Field-level dashboard | Quick view of daily submission activity |
| **Submissions** | All or division-scoped submissions | Review and score field work |
| **Rapid Review** | Swipe queue | Process reviews efficiently |
| **Standards Library** | All standards | Reference standards during field checks |
| **Team Members** | All profiles | Check crew performance |
| **Training Mode** | Training results | Monitor crew training completion |

### Key Observations
- Supervisors bridge the gap between Production Managers and field crews.
- Use the Standards Library as a field reference — share specific standards with crews before they start work.
- Your review scores feed into the calibration heatmap — consistent scoring is critical.

---

## CREW LEADER (Alejandro, Marcus, Derek, Nathan)

### Pages Available (Crew Portal — no login required)
| Tab | What You See | What You Do |
|-----|-------------|-------------|
| **Work Capture** | Photo submission form | Take photos, select task type, add GPS, submit |
| **Standards** | Standards for your division | Review quality expectations before shooting |
| **Equipment** | Maintenance log | Log equipment checks, red-tag damaged equipment |
| **My Team** | Your crew members | View who's on your team, manage members |

### Key Features
- **Division Switcher**: In the Standards tab, tap any division pill to view that division's standards. Use case: you finish an Install wall job and hop over to help Maintenance with pruning — switch to Maintenance standards to know the expectations.
- **Photo Submission**: Wide establishing shot → detail shot → client-view shot. Follow the Photo Documentation Standard.
- **Red Tag**: If equipment fails pre-check, red-tag it. This immediately notifies PMs, Supervisors, GM, and Owner.

### Key Observations
- Your crew access code is your identity. Share it only with your team for member registration.
- Standards are filtered by your division by default — but you can switch divisions when doing cross-division work.
- Every submission is reviewed by management. Quality photos = faster, fairer reviews.

---

## CREW MEMBER (Alex, Carlos, James, Luis, Ryan, Kevin, Miguel, Tyler, David)

### Pages Available (Personal Dashboard — QR registration required)
| Section | What You See | What You Do |
|---------|-------------|-------------|
| **Dashboard** | Your assigned crew, division, leader | View your placement and team |
| **Standards** | Standards for your division | Study quality expectations |

### Key Observations
- You register via your crew leader's QR code. Your dashboard shows your team info.
- Review the Standards Library regularly — training quizzes are based on these standards.
- Your submissions (through your crew leader's portal) are tracked to your crew's record.

---

## SYSTEM TRUST POINTS

1. **Every submission is reviewed** — nothing goes unscored.
2. **Scores are calibrated** — the Analytics heatmap ensures reviewers score consistently.
3. **Repeat issues are tracked** — the system identifies patterns, not just individual failures.
4. **Training is connected to standards** — if you fail a standard, you'll see it in your training queue.
5. **Data is real** — GPS, timestamps, and photos create an auditable trail.
6. **Role access is enforced** — you only see what your role requires. No more, no less.

---

## QUICK REFERENCE: PAGE ACCESS MATRIX

| Page | Owner | GM | PM | AM | Supervisor | Crew Leader | Crew Member |
|------|-------|----|----|-----|------------|-------------|-------------|
| Overview | Full | Full | Division | Cross | Field | — | — |
| Submissions | All | All | Division | All | All | Submit only | — |
| Rapid Review | All | All | Division | — | All | — | — |
| Standards Library | CRUD | CRUD | Read | Read | Read | Read (div) | Read (div) |
| QJA | Full | Full | Division | — | — | — | — |
| Team Members | Full | Full | Read | Read | Read | — | — |
| Analytics | Full | Full | — | — | — | — | — |
| Training Mode | Full | Full | Division | — | Division | — | — |
| Repeat Offenders | Full | Full | Division | — | Division | — | — |
| Crew Portal | — | — | — | — | — | Full | — |
| Member Dashboard | — | — | — | — | — | — | Read |

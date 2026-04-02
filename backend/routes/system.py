from fastapi import APIRouter, Depends

from shared.deps import now_iso, require_roles

router = APIRouter()

SYSTEM_BLUEPRINT = {
    "architecture": {
        "frontend": [
            "Public crew capture portal via unique QR route with free-text job name entry",
            "Protected admin and owner dashboards with role-aware navigation",
            "System blueprint page for architecture, schema, and rollout planning",
        ],
        "backend": [
            "FastAPI API with JWT auth, job alignment import, submissions, issue intake, reviews, exports, analytics",
            "MongoDB collections using string IDs for AI-ready relational linking",
            "Supabase Storage service layer for proof images and review-ready asset retrieval",
        ],
        "storage": [
            "Supabase bucket-backed image storage managed by the backend service role",
            "Stable backend-served image routes for admin and owner review screens",
            "Export bundle generation for JSONL and CSV",
        ],
    },
    "database_schema": [
        "jobs", "submissions", "rapid_reviews", "standards_library",
        "training_sessions", "management_reviews", "owner_reviews",
        "rubric_definitions", "users", "export_records", "crew_access_links",
        "drive_credentials", "notifications",
    ],
    "ui_screens": [
        "Login & system access",
        "Crew mobile capture portal",
        "Operations overview dashboard",
        "Jobs alignment import & QR access management",
        "Management review queue",
        "Owner-only calibration & dataset approval",
        "Owner analytics and exports workspace",
        "Integration settings and blueprint reference",
    ],
    "workflow_diagram": [
        "Draft", "Submitted", "Pending Match", "Ready for Review",
        "Management Reviewed", "Owner Reviewed", "Finalized",
        "Export Ready", "Exported",
    ],
    "suggested_stack": {
        "frontend": "React 19 + Tailwind + shadcn/ui + Framer Motion",
        "backend": "FastAPI + Motor + JWT auth + Supabase Storage",
        "database": "MongoDB with collection-per-module structure",
    },
    "implementation_plan": [
        "Crew capture and file persistence",
        "CSV job import and auto-match scoring",
        "Management rubric review flow",
        "Owner calibration and training inclusion",
        "Analytics, exports, and Supabase-backed photo retrieval",
    ],
}


@router.get("/")
async def root():
    return {"message": "Field Quality Capture & Review System API"}


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": now_iso()}


@router.get("/system/blueprint")
async def get_blueprint(user: dict = Depends(require_roles("management", "owner"))):
    return SYSTEM_BLUEPRINT

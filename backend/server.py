import csv
import io
import json
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from auth_utils import create_access_token, decode_access_token, get_password_hash, verify_password
from drive_sync import (
    SCOPES,
    build_oauth_flow,
    credentials_to_document,
    dump_json_bytes,
    get_authorization_url,
    is_drive_configured,
    sync_submission_bundle,
)


ROOT_DIR = Path(__file__).parent
DATA_DIR = Path("/app/data")
SUBMISSIONS_DIR = DATA_DIR / "submissions"
EXPORTS_DIR = DATA_DIR / "exports"
load_dotenv(ROOT_DIR / ".env")


mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Field Quality Capture & Review System")
api_router = APIRouter(prefix="/api")
bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utc_now().isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def serialize(document: dict | None) -> dict | None:
    if not document:
        return None
    return {key: value for key, value in document.items() if key != "_id"}


def audit_entry(action: str, actor_id: str | None, note: str = "") -> dict:
    return {
        "timestamp": now_iso(),
        "action": action,
        "actor_id": actor_id,
        "note": note,
    }


def normalize_key(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def write_json_artifact(folder_path: str | None, filename: str, payload: dict) -> None:
    if not folder_path:
        return
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(dump_json_bytes(payload))


def present_crew_link(crew_link: dict) -> dict:
    return {
        **crew_link,
        "crew_member_id": crew_link.get("crew_member_id") or crew_link.get("code", "").upper(),
    }


class LoginRequest(BaseModel):
    email: str
    password: str


class CrewAccessCreate(BaseModel):
    label: str
    truck_number: str
    division: str


class MatchOverrideRequest(BaseModel):
    job_id: str
    service_type: str | None = None


class ManagementReviewRequest(BaseModel):
    submission_id: str
    job_id: str | None = None
    service_type: str
    category_scores: dict[str, float]
    comments: str = ""
    disposition: str
    flagged_issues: list[str] = Field(default_factory=list)


class OwnerReviewRequest(BaseModel):
    submission_id: str
    category_scores: dict[str, float]
    comments: str = ""
    final_disposition: str
    training_inclusion: str
    exclusion_reason: str = ""


class ExportRunRequest(BaseModel):
    dataset_type: str
    export_format: str


class UserCreateRequest(BaseModel):
    name: str
    email: str
    role: str = "management"
    title: str
    password: str
    is_active: bool = True


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class CrewLinkStatusUpdateRequest(BaseModel):
    enabled: bool


RUBRIC_LIBRARY = [
    {
        "id": "rubric_bed_edging_v1",
        "service_type": "bed edging",
        "title": "Bed Edging v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 78,
        "hard_fail_conditions": ["property_damage", "unsafe_debris_left_behind"],
        "categories": [
            {"key": "continuity", "label": "Continuity", "weight": 0.22, "max_score": 5},
            {"key": "depth_consistency", "label": "Depth Consistency", "weight": 0.24, "max_score": 5},
            {"key": "turf_containment", "label": "Turf Containment", "weight": 0.18, "max_score": 5},
            {"key": "cleanliness", "label": "Cleanliness", "weight": 0.16, "max_score": 5},
            {"key": "visual_finish", "label": "Visual Finish", "weight": 0.2, "max_score": 5},
        ],
    },
    {
        "id": "rubric_spring_cleanup_v1",
        "service_type": "spring cleanup",
        "title": "Spring Cleanup v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 80,
        "hard_fail_conditions": ["missed_debris_zone", "damaged_bed_material"],
        "categories": [
            {"key": "coverage", "label": "Coverage", "weight": 0.24, "max_score": 5},
            {"key": "cleanliness", "label": "Cleanliness", "weight": 0.24, "max_score": 5},
            {"key": "bed_definition", "label": "Bed Definition", "weight": 0.18, "max_score": 5},
            {"key": "turf_finish", "label": "Turf Finish", "weight": 0.16, "max_score": 5},
            {"key": "curb_appeal", "label": "Curb Appeal", "weight": 0.18, "max_score": 5},
        ],
    },
    {
        "id": "rubric_fall_cleanup_v1",
        "service_type": "fall cleanup",
        "title": "Fall Cleanup v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 81,
        "hard_fail_conditions": ["leaf_buildup_remaining", "blocked_drainage"],
        "categories": [
            {"key": "leaf_removal", "label": "Leaf Removal", "weight": 0.26, "max_score": 5},
            {"key": "detail_finish", "label": "Detail Finish", "weight": 0.2, "max_score": 5},
            {"key": "bed_cleanup", "label": "Bed Cleanup", "weight": 0.18, "max_score": 5},
            {"key": "walkway_clearance", "label": "Walkway Clearance", "weight": 0.18, "max_score": 5},
            {"key": "visual_finish", "label": "Visual Finish", "weight": 0.18, "max_score": 5},
        ],
    },
]


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
            "Google Drive sync service with OAuth connection and structured folders",
        ],
        "storage": [
            "Local file cache for uploaded photos and JSON artifacts",
            "Google Drive mirror using /QA/{Year}/{Division}/{ServiceType}/{JobID}_{SubmissionID}",
            "Export bundle generation for JSONL and CSV",
        ],
    },
    "database_schema": [
        "jobs",
        "submissions",
        "management_reviews",
        "owner_reviews",
        "rubric_definitions",
        "users",
        "export_records",
        "crew_access_links",
        "drive_credentials",
        "notifications",
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
        "Draft",
        "Submitted",
        "Pending Match",
        "Ready for Review",
        "Management Reviewed",
        "Owner Reviewed",
        "Finalized",
        "Export Ready",
        "Exported",
    ],
    "suggested_stack": {
        "frontend": "React 19 + Tailwind + shadcn/ui + Framer Motion",
        "backend": "FastAPI + Motor + JWT auth + Google Drive API",
        "database": "MongoDB with collection-per-module structure",
    },
    "implementation_plan": [
        "Crew capture and file persistence",
        "CSV job import and auto-match scoring",
        "Management rubric review flow",
        "Owner calibration and training inclusion",
        "Analytics, exports, and Google Drive sync",
    ],
}


def compute_match(job: dict | None, truck_number: str, gps_lat: float, gps_lng: float) -> tuple[str, float]:
    if not job:
        return "unmatched", 0.0
    confidence = 0.55
    if job.get("truck_number") and job["truck_number"].lower() == truck_number.lower():
        confidence += 0.2
    scheduled = job.get("scheduled_date")
    if scheduled:
        try:
            delta = abs((datetime.fromisoformat(scheduled) - utc_now()).days)
            confidence += 0.15 if delta <= 1 else 0.05
        except ValueError:
            pass
    if job.get("latitude") and job.get("longitude"):
        distance = haversine_distance_km(gps_lat, gps_lng, float(job["latitude"]), float(job["longitude"]))
        confidence += 0.1 if distance <= 0.5 else 0.03 if distance <= 3 else 0
    confidence = min(round(confidence, 2), 0.99)
    status = "confirmed" if confidence >= 0.85 else "suggested" if confidence >= 0.65 else "unmatched"
    return status, confidence


async def get_active_rubric(service_type: str) -> dict:
    rubric = await db.rubric_definitions.find_one(
        {"service_type": service_type.lower(), "is_active": True}, {"_id": 0}, sort=[("version", -1)]
    )
    if not rubric:
        raise HTTPException(status_code=400, detail=f"No rubric configured for {service_type}")
    return rubric


def calculate_total_score(rubric: dict, category_scores: dict[str, float]) -> float:
    total = 0.0
    for category in rubric["categories"]:
        raw_score = max(0.0, min(float(category_scores.get(category["key"], 0)), category["max_score"]))
        total += (raw_score / category["max_score"]) * category["weight"]
    return round(total * 100, 1)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    return user


def require_roles(*allowed_roles: str):
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


async def create_submission_snapshot(submission_id: str) -> dict:
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    management_review = await db.management_reviews.find_one({"submission_id": submission_id}, {"_id": 0})
    owner_review = await db.owner_reviews.find_one({"submission_id": submission_id}, {"_id": 0})
    job = None
    if submission.get("matched_job_id"):
        job = await db.jobs.find_one({"id": submission["matched_job_id"]}, {"_id": 0})
    rubric = None
    if submission.get("service_type"):
        rubric = await db.rubric_definitions.find_one(
            {"service_type": submission["service_type"].lower(), "is_active": True}, {"_id": 0}, sort=[("version", -1)]
        )
    return {
        "submission": submission,
        "management_review": management_review,
        "owner_review": owner_review,
        "job": job,
        "rubric": rubric,
    }


async def create_notification(
    title: str,
    message: str,
    audience: str,
    related_submission_id: str | None = None,
    target_role: str | None = None,
    target_titles: list[str] | None = None,
    target_access_code: str | None = None,
    target_user_id: str | None = None,
    related_job_id: str | None = None,
    notification_type: str = "info",
) -> dict:
    notification = {
        "id": make_id("note"),
        "title": title,
        "message": message,
        "audience": audience,
        "target_role": target_role,
        "target_titles": target_titles or [],
        "target_access_code": target_access_code,
        "target_user_id": target_user_id,
        "related_submission_id": related_submission_id,
        "related_job_id": related_job_id,
        "notification_type": notification_type,
        "status": "unread",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", "system", title)],
    }
    await db.notifications.insert_one({**notification})
    return notification


async def seed_defaults() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    users = [
        {
            "name": "Maya Manager",
            "email": "management@fieldquality.local",
            "role": "management",
            "title": "Production Manager",
        },
        {
            "name": "Gina GM",
            "email": "gm@fieldquality.local",
            "role": "management",
            "title": "GM",
        },
        {
            "name": "Avery Account Manager",
            "email": "account.manager@fieldquality.local",
            "role": "management",
            "title": "Account Manager",
        },
        {
            "name": "Parker Production Manager",
            "email": "production.manager@fieldquality.local",
            "role": "management",
            "title": "Production Manager",
        },
        {
            "name": "Sam Supervisor",
            "email": "supervisor@fieldquality.local",
            "role": "management",
            "title": "Supervisor",
        },
        {
            "name": "Owen Owner",
            "email": "owner@fieldquality.local",
            "role": "owner",
            "title": "Owner",
        },
    ]
    for user in users:
        existing = await db.users.find_one({"email": user["email"]}, {"_id": 0})
        if existing:
            await db.users.update_one(
                {"email": user["email"]},
                {
                    "$set": {
                        "name": user["name"],
                        "role": user["role"],
                        "title": user["title"],
                        "is_active": True,
                        "updated_at": now_iso(),
                    }
                },
            )
        else:
            await db.users.insert_one(
                {
                    "id": make_id("user"),
                    **user,
                    "password_hash": get_password_hash("FieldQA123!"),
                    "is_active": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", f"{user['title']} demo account created")],
                }
            )

    await db.jobs.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.crew_access_links.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.submissions.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})

    if await db.rubric_definitions.count_documents({}) == 0:
        payload = []
        for rubric in RUBRIC_LIBRARY:
            payload.append(
                {
                    **rubric,
                    "is_active": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", f"Rubric {rubric['title']} loaded")],
                }
            )
        await db.rubric_definitions.insert_many(payload)

    if await db.crew_access_links.count_documents({}) == 0:
        crew_links = [
            {"label": "North Crew", "truck_number": "TR-12", "division": "Install"},
            {"label": "Central Crew", "truck_number": "TR-18", "division": "Maintenance"},
            {"label": "South Crew", "truck_number": "TR-24", "division": "Cleanup"},
        ]
        await db.crew_access_links.insert_many(
            [
                {
                    "id": make_id("crew"),
                    "code": uuid.uuid4().hex[:8],
                    "crew_member_id": make_id("crewid").upper(),
                    **item,
                    "enabled": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", "Crew QR access created")],
                }
                for item in crew_links
            ]
        )

    if await db.jobs.count_documents({}) == 0:
        jobs = [
            {
                "id": make_id("job"),
                "job_id": "LMN-4101",
                "job_name": "Riverview Estates Entry Beds",
                "property_name": "Riverview Estates",
                "address": "101 Riverside Dr",
                "service_type": "bed edging",
                "scheduled_date": (utc_now() + timedelta(days=1)).isoformat(),
                "division": "Install",
                "truck_number": "TR-12",
                "route": "North Route",
                "source": "seed",
                "search_text": "lmn-4101 riverview estates entry beds",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
            {
                "id": make_id("job"),
                "job_id": "LMN-4102",
                "job_name": "Maple Grove Spring Reset",
                "property_name": "Maple Grove HOA",
                "address": "55 Maple Grove Ln",
                "service_type": "spring cleanup",
                "scheduled_date": utc_now().isoformat(),
                "division": "Maintenance",
                "truck_number": "TR-18",
                "route": "Central Route",
                "source": "seed",
                "search_text": "lmn-4102 maple grove spring cleanup",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
            {
                "id": make_id("job"),
                "job_id": "LMN-4103",
                "job_name": "Willow Creek Fall Cleanup",
                "property_name": "Willow Creek Office Park",
                "address": "880 Willow Pkwy",
                "service_type": "fall cleanup",
                "scheduled_date": (utc_now() - timedelta(days=1)).isoformat(),
                "division": "Cleanup",
                "truck_number": "TR-24",
                "route": "South Route",
                "source": "seed",
                "search_text": "lmn-4103 willow creek fall cleanup",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
        ]
        await db.jobs.insert_many(jobs)

    if await db.submissions.count_documents({}) == 0:
        jobs = await db.jobs.find({}, {"_id": 0}).to_list(10)
        crew_links = await db.crew_access_links.find({}, {"_id": 0}).to_list(10)
        if jobs and crew_links:
            ready_job = jobs[0]
            reviewed_job = jobs[1]
            finalized_job = jobs[2]
            ready_submission_id = make_id("sub")
            reviewed_submission_id = make_id("sub")
            finalized_submission_id = make_id("sub")
            samples = [
                {
                    "id": ready_submission_id,
                    "submission_code": ready_submission_id.upper(),
                    "access_code": crew_links[0]["code"],
                    "crew_label": crew_links[0]["label"],
                    "job_id": ready_job["job_id"],
                    "matched_job_id": ready_job["id"],
                    "match_status": "confirmed",
                    "match_confidence": 0.94,
                    "truck_number": ready_job["truck_number"],
                    "division": ready_job["division"],
                    "service_type": ready_job["service_type"],
                    "status": "Ready for Review",
                    "note": "Seeded sample awaiting management scoring",
                    "area_tag": "Front entry",
                    "gps": {"lat": 43.631, "lng": -79.412, "accuracy": 7},
                    "captured_at": now_iso(),
                    "photo_count": 3,
                    "required_photo_count": 3,
                    "photo_files": [
                        {
                            "id": make_id("file"),
                            "filename": "seed-ready-1.jpg",
                            "mime_type": "image/jpeg",
                            "sequence": 1,
                            "source_type": "remote",
                            "media_url": "https://images.pexels.com/photos/6728925/pexels-photo-6728925.jpeg?auto=compress&cs=tinysrgb&w=1200",
                        }
                    ],
                    "drive_sync_status": "pending_configuration",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", "Sample submission created")],
                },
                {
                    "id": reviewed_submission_id,
                    "submission_code": reviewed_submission_id.upper(),
                    "access_code": crew_links[1]["code"],
                    "crew_label": crew_links[1]["label"],
                    "job_id": reviewed_job["job_id"],
                    "matched_job_id": reviewed_job["id"],
                    "match_status": "confirmed",
                    "match_confidence": 0.9,
                    "truck_number": reviewed_job["truck_number"],
                    "division": reviewed_job["division"],
                    "service_type": reviewed_job["service_type"],
                    "status": "Management Reviewed",
                    "note": "Cleanup completed with minor clippings left in curb line",
                    "area_tag": "Parking edge",
                    "gps": {"lat": 43.641, "lng": -79.401, "accuracy": 8},
                    "captured_at": now_iso(),
                    "photo_count": 4,
                    "required_photo_count": 4,
                    "photo_files": [
                        {
                            "id": make_id("file"),
                            "filename": "seed-review-1.jpg",
                            "mime_type": "image/jpeg",
                            "sequence": 1,
                            "source_type": "remote",
                            "media_url": "https://images.unsplash.com/photo-1696663118264-55a63c75409b?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                        }
                    ],
                    "drive_sync_status": "pending_configuration",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", "Sample submission created")],
                },
                {
                    "id": finalized_submission_id,
                    "submission_code": finalized_submission_id.upper(),
                    "access_code": crew_links[2]["code"],
                    "crew_label": crew_links[2]["label"],
                    "job_id": finalized_job["job_id"],
                    "matched_job_id": finalized_job["id"],
                    "match_status": "confirmed",
                    "match_confidence": 0.88,
                    "truck_number": finalized_job["truck_number"],
                    "division": finalized_job["division"],
                    "service_type": finalized_job["service_type"],
                    "status": "Export Ready",
                    "note": "Owner-approved gold sample",
                    "area_tag": "Rear drainage swale",
                    "gps": {"lat": 43.622, "lng": -79.392, "accuracy": 6},
                    "captured_at": now_iso(),
                    "photo_count": 4,
                    "required_photo_count": 4,
                    "photo_files": [
                        {
                            "id": make_id("file"),
                            "filename": "seed-owner-1.jpg",
                            "mime_type": "image/jpeg",
                            "sequence": 1,
                            "source_type": "remote",
                            "media_url": "https://images.unsplash.com/photo-1605117882932-f9e32b03fea9?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                        }
                    ],
                    "drive_sync_status": "pending_configuration",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", "Sample submission created")],
                },
            ]
            await db.submissions.insert_many(samples)

            management_user = await db.users.find_one({"role": "management"}, {"_id": 0})
            owner_user = await db.users.find_one({"role": "owner"}, {"_id": 0})
            spring_rubric = await get_active_rubric("spring cleanup")
            fall_rubric = await get_active_rubric("fall cleanup")
            management_review = {
                "id": make_id("mgr"),
                "submission_id": reviewed_submission_id,
                "reviewer_id": management_user["id"],
                "rubric_id": spring_rubric["id"],
                "rubric_version": spring_rubric["version"],
                "service_type": "spring cleanup",
                "category_scores": {
                    "coverage": 4,
                    "cleanliness": 4,
                    "bed_definition": 3,
                    "turf_finish": 4,
                    "curb_appeal": 4,
                },
                "total_score": 77.6,
                "comments": "Good reset overall, minor curb clippings remain.",
                "disposition": "pass with notes",
                "flagged_issues": ["curb_line_cleanup"],
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", management_user["id"], "Seed management review")],
            }
            owner_review = {
                "id": make_id("own"),
                "submission_id": finalized_submission_id,
                "reviewer_id": owner_user["id"],
                "rubric_id": fall_rubric["id"],
                "rubric_version": fall_rubric["version"],
                "service_type": "fall cleanup",
                "category_scores": {
                    "leaf_removal": 5,
                    "detail_finish": 4,
                    "bed_cleanup": 4,
                    "walkway_clearance": 5,
                    "visual_finish": 4,
                },
                "total_score": 90.8,
                "comments": "Excellent gold-standard cleanup example.",
                "final_disposition": "pass",
                "training_inclusion": "approved",
                "exclusion_reason": "",
                "variance_from_management": 2.4,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", owner_user["id"], "Seed owner review")],
            }
            await db.management_reviews.insert_one(management_review)
            await db.owner_reviews.insert_one(owner_review)


@app.on_event("startup")
async def startup_event():
    await seed_defaults()


@api_router.get("/")
async def root():
    return {"message": "Field Quality Capture & Review System API"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "timestamp": now_iso()}


@api_router.post("/auth/login")
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_access_token(user["id"], user["role"])
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {"last_login_at": now_iso(), "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("login", user["id"], "Successful login")},
        },
    )
    user.pop("password_hash", None)
    return {"token": token, "user": user}


@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@api_router.get("/system/blueprint")
async def get_blueprint(user: dict = Depends(require_roles("management", "owner"))):
    return SYSTEM_BLUEPRINT


@api_router.get("/public/crew-access")
async def get_public_crew_access():
    crew_links = await db.crew_access_links.find({"enabled": True}, {"_id": 0}).to_list(100)
    return [present_crew_link(link) for link in crew_links]


@api_router.get("/public/crew-access/{code}")
async def get_crew_access_link(code: str):
    crew_link = await db.crew_access_links.find_one({"code": code, "enabled": True}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    notifications = await db.notifications.find(
        {"audience": "crew", "target_access_code": code, "status": "unread"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(20)
    return {**present_crew_link(crew_link), "notifications": notifications}


@api_router.get("/public/jobs")
async def get_public_jobs(search: str = "", access_code: str | None = None):
    query: dict[str, Any] = {}
    crew_link = None
    if access_code:
        crew_link = await db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
        if crew_link:
            query["truck_number"] = crew_link["truck_number"]
    if search:
        query["search_text"] = {"$regex": search.lower()}
    jobs = await db.jobs.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(100)
    return {"jobs": jobs, "crew_link": crew_link}


@api_router.post("/public/submissions")
async def create_submission(
    background_tasks: BackgroundTasks,
    request: Request,
    access_code: str = Form(...),
    job_id: str = Form(""),
    job_name: str = Form(""),
    truck_number: str = Form(...),
    gps_lat: float = Form(...),
    gps_lng: float = Form(...),
    gps_accuracy: float = Form(0),
    note: str = Form(""),
    area_tag: str = Form(""),
    issue_type: str = Form(""),
    issue_notes: str = Form(""),
    photos: list[UploadFile] = File(...),
    issue_photos: list[UploadFile] = File([]),
):
    crew_link = await db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew access link not found")
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0}) if job_id else None
    if not job and not job_name.strip():
        raise HTTPException(status_code=400, detail="Job name is required")

    required_photo_count = 3
    if job and job.get("service_type"):
        rubric = await get_active_rubric(job["service_type"])
        required_photo_count = rubric.get("min_photos", 3)
    if len(photos) < required_photo_count:
        raise HTTPException(
            status_code=400,
            detail=f"At least {required_photo_count} photos are required for this submission",
        )

    recent_cutoff = (utc_now() - timedelta(minutes=15)).isoformat()
    job_key = job["job_id"] if job else job_name.strip().lower()
    duplicate = await db.submissions.find_one(
        {
            "job_key": job_key,
            "truck_number": truck_number,
            "created_at": {"$gte": recent_cutoff},
        },
        {"_id": 0},
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="A recent submission for this job and truck already exists")

    submission_id = make_id("sub")
    local_folder = SUBMISSIONS_DIR / submission_id
    local_folder.mkdir(parents=True, exist_ok=True)
    photo_files = []

    for index, photo in enumerate(photos, start=1):
        content = await photo.read()
        suffix = Path(photo.filename or f"capture-{index}.jpg").suffix or ".jpg"
        filename = f"{index:02d}_{uuid.uuid4().hex[:6]}{suffix}"
        file_path = local_folder / filename
        file_path.write_bytes(content)
        photo_files.append(
            {
                "id": make_id("file"),
                "filename": filename,
                "original_name": photo.filename,
                "mime_type": photo.content_type or "application/octet-stream",
                "sequence": index,
                "size_bytes": len(content),
                "local_path": str(file_path),
                "relative_api_path": f"/api/submissions/files/{submission_id}/{filename}",
                "media_url": f"{os.environ['FRONTEND_URL']}/api/submissions/files/{submission_id}/{filename}",
                "source_type": "local",
            }
        )

    field_report_photo_files = []
    for index, issue_photo in enumerate(issue_photos or [], start=1):
        content = await issue_photo.read()
        suffix = Path(issue_photo.filename or f"issue-{index}.jpg").suffix or ".jpg"
        filename = f"issue_{index:02d}_{uuid.uuid4().hex[:6]}{suffix}"
        file_path = local_folder / filename
        file_path.write_bytes(content)
        field_report_photo_files.append(
            {
                "id": make_id("issuefile"),
                "filename": filename,
                "original_name": issue_photo.filename,
                "mime_type": issue_photo.content_type or "application/octet-stream",
                "sequence": index,
                "local_path": str(file_path),
                "relative_api_path": f"/api/submissions/files/{submission_id}/{filename}",
                "media_url": f"{os.environ['FRONTEND_URL']}/api/submissions/files/{submission_id}/{filename}",
                "source_type": "local",
            }
        )

    match_status, match_confidence = compute_match(job, truck_number, gps_lat, gps_lng) if job else ("unmatched", 0.0)
    status = "Ready for Review" if job and match_status in {"confirmed", "suggested"} else "Pending Match"
    job_name_value = job["job_name"] if job else job_name.strip()
    submission = {
        "id": submission_id,
        "submission_code": submission_id.upper(),
        "access_code": access_code,
        "crew_label": crew_link["label"],
        "job_key": job_key,
        "job_id": job["job_id"] if job else None,
        "job_name_input": job_name_value,
        "matched_job_id": job["id"] if job else None,
        "match_status": match_status,
        "match_confidence": match_confidence,
        "truck_number": truck_number,
        "division": job["division"] if job else crew_link["division"],
        "service_type": job["service_type"] if job else "",
        "status": status,
        "note": note,
        "area_tag": area_tag,
        "field_report": {
            "type": issue_type,
            "notes": issue_notes,
            "photo_files": field_report_photo_files,
            "reported": bool(issue_type or issue_notes or field_report_photo_files),
        },
        "gps": {"lat": gps_lat, "lng": gps_lng, "accuracy": gps_accuracy},
        "captured_at": now_iso(),
        "required_photo_count": required_photo_count,
        "photo_count": len(photo_files),
        "photo_files": photo_files,
        "local_folder_path": str(local_folder),
        "device_metadata": {"user_agent": request.headers.get("user-agent", "unknown")},
        "drive_sync_status": "pending_configuration",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [
            audit_entry("submitted", access_code, "Crew submission created"),
            audit_entry("status_change", access_code, f"Lifecycle moved to {status}"),
        ],
    }
    write_json_artifact(str(local_folder), "metadata.json", submission)
    await db.notifications.update_many(
        {
            "audience": "crew",
            "target_access_code": access_code,
            "related_job_id": job_key,
            "status": "unread",
        },
        {
            "$set": {"status": "resolved", "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("resolved", access_code, "Crew submitted follow-up proof")},
        },
    )
    await db.submissions.insert_one({**submission})
    await create_notification(
        title="New crew submission ready",
        message=f"{crew_link['label']} submitted {job_name_value} for management review.",
        audience="management",
        target_role="management",
        related_submission_id=submission_id,
        related_job_id=job_key,
        notification_type="new_submission",
    )
    if submission["field_report"]["reported"]:
        await create_notification(
            title="Crew reported an issue or damage",
            message=f"{crew_link['label']} reported '{issue_type or 'field issue'}' on {job_name_value}.",
            audience="management",
            target_titles=["Production Manager", "Account Manager"],
            related_submission_id=submission_id,
            related_job_id=job_key,
            notification_type="field_issue",
        )
    background_tasks.add_task(sync_submission_bundle, db, submission)
    return {"submission": submission}


@api_router.get("/submissions/files/{submission_id}/{filename}")
async def get_submission_file(submission_id: str, filename: str):
    file_path = SUBMISSIONS_DIR / submission_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@api_router.get("/dashboard/overview")
async def get_dashboard_overview(user: dict = Depends(require_roles("management", "owner"))):
    submissions = await db.submissions.find({}, {"_id": 0}).to_list(1000)
    jobs_count = await db.jobs.count_documents({})
    rubrics_count = await db.rubric_definitions.count_documents({})
    export_count = await db.export_records.count_documents({})
    management_queue = len([item for item in submissions if item["status"] in {"Pending Match", "Ready for Review"}])
    owner_queue = len([item for item in submissions if item["status"] in {"Management Reviewed", "Owner Reviewed"}])
    export_ready = len([item for item in submissions if item["status"] == "Export Ready"])
    review_velocity = round((management_queue + owner_queue + export_ready) / max(len(submissions), 1) * 100, 1)
    return {
        "totals": {
            "submissions": len(submissions),
            "jobs": jobs_count,
            "rubrics": rubrics_count,
            "exports": export_count,
        },
        "queues": {
            "management": management_queue,
            "owner": owner_queue,
            "export_ready": export_ready,
        },
        "drive": {
            "configured": is_drive_configured(),
            "connected": await db.drive_credentials.count_documents({}) > 0,
            "scope": SCOPES,
        },
        "workflow_health": {
            "review_velocity_percent": review_velocity,
            "duplicate_guard_window_minutes": 15,
        },
    }


@api_router.get("/jobs")
async def get_jobs(user: dict = Depends(require_roles("management", "owner")), search: str = ""):
    query: dict[str, Any] = {}
    if search:
        query["search_text"] = {"$regex": search.lower()}
    jobs = await db.jobs.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(500)
    return jobs


@api_router.post("/jobs/import-csv")
async def import_jobs_csv(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("management", "owner")),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    imported = 0
    updated = 0
    normalized_rows = []
    for row in reader:
        normalized = {normalize_key(key): (value or "").strip() for key, value in row.items()}
        if not normalized.get("job_id"):
            continue
        scheduled_raw = normalized.get("scheduled_date") or normalized.get("date") or now_iso()
        try:
            scheduled_date = datetime.fromisoformat(scheduled_raw).isoformat()
        except ValueError:
            scheduled_date = now_iso()
        job_payload = {
            "job_id": normalized.get("job_id"),
            "job_name": normalized.get("job_name") or normalized.get("job") or normalized.get("property_name"),
            "property_name": normalized.get("property_name") or normalized.get("job_name") or normalized.get("job"),
            "address": normalized.get("address") or normalized.get("property_address"),
            "service_type": (normalized.get("service_type") or "bed edging").lower(),
            "scheduled_date": scheduled_date,
            "division": normalized.get("division") or "General",
            "truck_number": normalized.get("truck_number") or normalized.get("truck") or "Unassigned",
            "route": normalized.get("route") or "",
            "latitude": normalized.get("latitude") or None,
            "longitude": normalized.get("longitude") or None,
            "source": "csv_import",
            "search_text": " ".join(
                filter(
                    None,
                    [
                        normalized.get("job_id"),
                        normalized.get("job_name"),
                        normalized.get("property_name"),
                        normalized.get("address"),
                    ],
                )
            ).lower(),
            "updated_at": now_iso(),
        }
        existing = await db.jobs.find_one({"job_id": job_payload["job_id"]}, {"_id": 0})
        if existing:
            await db.jobs.update_one(
                {"id": existing["id"]},
                {
                    "$set": job_payload,
                    "$push": {"audit_history": audit_entry("updated", user["id"], "CSV import refreshed job")},
                },
            )
            updated += 1
        else:
            normalized_rows.append(
                {
                    "id": make_id("job"),
                    **job_payload,
                    "created_at": now_iso(),
                    "audit_history": [audit_entry("created", user["id"], "CSV import created job")],
                }
            )
            imported += 1

    if normalized_rows:
        await db.jobs.insert_many(normalized_rows)

    return {"imported": imported, "updated": updated, "filename": file.filename}


@api_router.get("/crew-access-links")
async def get_crew_access_links(user: dict = Depends(require_roles("management", "owner"))):
    crew_links = await db.crew_access_links.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [present_crew_link(link) for link in crew_links]


@api_router.post("/crew-access-links")
async def create_crew_access_link(payload: CrewAccessCreate, user: dict = Depends(require_roles("management", "owner"))):
    crew_link = {
        "id": make_id("crew"),
        "code": uuid.uuid4().hex[:8],
        "crew_member_id": make_id("crewid").upper(),
        "label": payload.label,
        "truck_number": payload.truck_number,
        "division": payload.division,
        "enabled": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], "Crew QR link created")],
    }
    await db.crew_access_links.insert_one({**crew_link})
    return present_crew_link(crew_link)


@api_router.patch("/crew-access-links/{crew_link_id}/status")
async def update_crew_access_link_status(
    crew_link_id: str,
    payload: CrewLinkStatusUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    await db.crew_access_links.update_one(
        {"id": crew_link_id},
        {
            "$set": {"enabled": payload.enabled, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("status_update", user["id"], f"enabled={payload.enabled}")},
        },
    )
    crew_link = await db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    return present_crew_link(crew_link)


@api_router.get("/users")
async def get_users(user: dict = Depends(require_roles("management", "owner"))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(200)
    return users


@api_router.post("/users")
async def create_user(payload: UserCreateRequest, user: dict = Depends(require_roles("management", "owner"))):
    existing = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    record = {
        "id": make_id("user"),
        "name": payload.name,
        "email": payload.email.lower(),
        "role": payload.role,
        "title": payload.title,
        "password_hash": get_password_hash(payload.password),
        "is_active": payload.is_active,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], f"Staff account created for {payload.title}")],
    }
    await db.users.insert_one({**record})
    record.pop("password_hash", None)
    return record


@api_router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {"is_active": payload.is_active, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("status_update", user["id"], f"active={payload.is_active}")},
        },
    )
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@api_router.get("/notifications")
async def get_notifications(
    user: dict = Depends(require_roles("management", "owner")),
    status: str = Query("all"),
):
    targets = [{"target_role": user["role"]}, {"target_user_id": user["id"]}]
    if user.get("title"):
        targets.append({"target_titles": user["title"]})
    query: dict[str, Any] = {"$or": targets}
    if status != "all":
        query["status"] = status
    notifications = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    unread_count = len([item for item in notifications if item.get("status") == "unread"])
    return {"items": notifications, "unread_count": unread_count}


@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(require_roles("management", "owner"))):
    targets = [{"target_role": user["role"]}, {"target_user_id": user["id"]}]
    if user.get("title"):
        targets.append({"target_titles": user["title"]})
    await db.notifications.update_one(
        {"id": notification_id, "$or": targets},
        {
            "$set": {"status": "read", "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("read", user["id"], "Notification opened")},
        },
    )
    return {"ok": True}


@api_router.get("/rubrics")
async def get_rubrics(user: dict = Depends(require_roles("management", "owner"))):
    rubrics = await db.rubric_definitions.find({"is_active": True}, {"_id": 0}).sort("service_type", 1).to_list(50)
    return rubrics


@api_router.get("/submissions")
async def get_submissions(
    user: dict = Depends(require_roles("management", "owner")),
    scope: str = Query("all"),
    filter_by: str = Query("all"),
):
    submissions = await db.submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    if scope == "management":
        submissions = [item for item in submissions if item["status"] in {"Pending Match", "Ready for Review", "Management Reviewed"}]
    elif scope == "owner":
        submissions = [item for item in submissions if item["status"] in {"Management Reviewed", "Owner Reviewed", "Export Ready"}]

    if filter_by == "low_confidence":
        submissions = [item for item in submissions if item.get("match_confidence", 0) < 0.8]
    elif filter_by == "incomplete_photo_sets":
        submissions = [item for item in submissions if item.get("photo_count", 0) < item.get("required_photo_count", 0)]
    elif filter_by == "flagged":
        flagged_ids = [item["submission_id"] for item in await db.management_reviews.find({"flagged_issues": {"$ne": []}}, {"_id": 0, "submission_id": 1}).to_list(1000)]
        submissions = [item for item in submissions if item["id"] in flagged_ids]
    return submissions


@api_router.get("/submissions/{submission_id}")
async def get_submission_detail(submission_id: str, user: dict = Depends(require_roles("management", "owner"))):
    return await create_submission_snapshot(submission_id)


@api_router.post("/submissions/{submission_id}/match")
async def override_submission_match(
    submission_id: str,
    payload: MatchOverrideRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_roles("management", "owner")),
):
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    job = await db.jobs.find_one({"id": payload.job_id}, {"_id": 0})
    if not submission or not job:
        raise HTTPException(status_code=404, detail="Submission or job not found")
    new_service_type = payload.service_type or job["service_type"]
    update = {
        "matched_job_id": job["id"],
        "job_id": job["job_id"],
        "service_type": new_service_type,
        "division": job["division"],
        "match_status": "confirmed",
        "match_confidence": 0.98,
        "status": "Ready for Review",
        "updated_at": now_iso(),
    }
    await db.submissions.update_one(
        {"id": submission_id},
        {
            "$set": update,
            "$push": {"audit_history": audit_entry("match_override", user["id"], f"Matched to {job['job_id']}")},
        },
    )
    snapshot = await create_submission_snapshot(submission_id)
    write_json_artifact(snapshot["submission"].get("local_folder_path"), "metadata.json", snapshot["submission"])
    background_tasks.add_task(sync_submission_bundle, db, snapshot["submission"])
    return snapshot


@api_router.post("/reviews/management")
async def create_management_review(
    payload: ManagementReviewRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_roles("management", "owner")),
):
    submission = await db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    rubric = await get_active_rubric(payload.service_type)
    total_score = calculate_total_score(rubric, payload.category_scores)
    review = {
        "id": make_id("mgr"),
        "submission_id": payload.submission_id,
        "reviewer_id": user["id"],
        "rubric_id": rubric["id"],
        "rubric_version": rubric["version"],
        "service_type": payload.service_type,
        "category_scores": payload.category_scores,
        "total_score": total_score,
        "comments": payload.comments,
        "disposition": payload.disposition,
        "flagged_issues": payload.flagged_issues,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], "Management review submitted")],
    }
    await db.management_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await db.submissions.update_one(
        {"id": payload.submission_id},
        {
            "$set": {
                "status": "Management Reviewed",
                "service_type": payload.service_type,
                "updated_at": now_iso(),
            },
            "$push": {"audit_history": audit_entry("management_reviewed", user["id"], payload.disposition)},
        },
    )
    await create_notification(
        title="Submission ready for owner review",
        message=f"{submission.get('job_name_input') or submission.get('job_id') or submission['submission_code']} was reviewed by management and is ready for owner calibration.",
        audience="owner",
        target_role="owner",
        related_submission_id=payload.submission_id,
        related_job_id=submission.get("job_id") or submission.get("job_key"),
        notification_type="owner_review",
    )
    if payload.disposition in {"correction required", "insufficient evidence"}:
        await create_notification(
            title="More photos requested",
            message=payload.comments or "Management requested a new photo upload for this job.",
            audience="crew",
            target_access_code=submission["access_code"],
            related_submission_id=payload.submission_id,
            related_job_id=submission.get("job_id") or submission.get("job_key"),
            notification_type="crew_followup",
        )
    write_json_artifact(submission.get("local_folder_path"), "management_review.json", review)
    updated_submission = await db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    background_tasks.add_task(sync_submission_bundle, db, updated_submission)
    return {"review": review, "submission": updated_submission}


@api_router.post("/reviews/owner")
async def create_owner_review(
    payload: OwnerReviewRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_roles("owner")),
):
    submission = await db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    rubric = await get_active_rubric(submission["service_type"])
    total_score = calculate_total_score(rubric, payload.category_scores)
    management_review = await db.management_reviews.find_one({"submission_id": payload.submission_id}, {"_id": 0})
    variance = round(abs(total_score - (management_review or {}).get("total_score", total_score)), 1)
    review = {
        "id": make_id("own"),
        "submission_id": payload.submission_id,
        "reviewer_id": user["id"],
        "rubric_id": rubric["id"],
        "rubric_version": rubric["version"],
        "service_type": submission["service_type"],
        "category_scores": payload.category_scores,
        "total_score": total_score,
        "comments": payload.comments,
        "final_disposition": payload.final_disposition,
        "training_inclusion": payload.training_inclusion,
        "exclusion_reason": payload.exclusion_reason,
        "variance_from_management": variance,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], "Owner review submitted")],
    }
    await db.owner_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await db.submissions.update_one(
        {"id": payload.submission_id},
        {
            "$set": {
                "status": "Export Ready",
                "final_disposition": payload.final_disposition,
                "training_inclusion": payload.training_inclusion,
                "updated_at": now_iso(),
            },
            "$push": {"audit_history": audit_entry("owner_reviewed", user["id"], payload.final_disposition)},
        },
    )
    if payload.final_disposition in {"correction required", "insufficient evidence"}:
        await create_notification(
            title="Owner requested another photo set",
            message=payload.comments or "Owner review requires new field photos before final approval.",
            audience="crew",
            target_access_code=submission["access_code"],
            related_submission_id=payload.submission_id,
            related_job_id=submission.get("job_id") or submission.get("job_key"),
            notification_type="crew_followup",
        )
    write_json_artifact(submission.get("local_folder_path"), "owner_review.json", review)
    updated_submission = await db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    background_tasks.add_task(sync_submission_bundle, db, updated_submission)
    return {"review": review, "submission": updated_submission}


@api_router.get("/analytics/summary")
async def get_analytics_summary(user: dict = Depends(require_roles("management", "owner"))):
    submissions = await db.submissions.find({}, {"_id": 0}).to_list(2000)
    management_reviews = await db.management_reviews.find({}, {"_id": 0}).to_list(2000)
    owner_reviews = await db.owner_reviews.find({}, {"_id": 0}).to_list(2000)

    crew_scores: dict[str, list[float]] = {}
    variance_points = []
    fail_reasons: dict[str, int] = {}
    volume_by_day: dict[str, int] = {}

    for submission in submissions:
        day_key = submission["created_at"][:10]
        volume_by_day[day_key] = volume_by_day.get(day_key, 0) + 1

    mgmt_lookup = {review["submission_id"]: review for review in management_reviews}
    owner_lookup = {review["submission_id"]: review for review in owner_reviews}

    for submission in submissions:
        crew_key = submission.get("crew_label") or submission.get("truck_number")
        if submission["id"] in owner_lookup:
            crew_scores.setdefault(crew_key, []).append(owner_lookup[submission["id"]]["total_score"])
        elif submission["id"] in mgmt_lookup:
            crew_scores.setdefault(crew_key, []).append(mgmt_lookup[submission["id"]]["total_score"])

    for submission_id, review in owner_lookup.items():
        variance_points.append({"submission_id": submission_id, "variance": review.get("variance_from_management", 0)})
        if review["training_inclusion"] == "excluded":
            key = review.get("exclusion_reason") or "excluded_without_reason"
            fail_reasons[key] = fail_reasons.get(key, 0) + 1

    for review in management_reviews:
        for issue in review.get("flagged_issues", []):
            fail_reasons[issue] = fail_reasons.get(issue, 0) + 1

    average_by_crew = [
        {"crew": crew, "average_score": round(sum(scores) / len(scores), 1)}
        for crew, scores in crew_scores.items()
    ]
    average_by_crew.sort(key=lambda item: item["average_score"], reverse=True)
    variance_avg = round(sum(point["variance"] for point in variance_points) / max(len(variance_points), 1), 1)

    heatmap_tracker: dict[tuple[str, str], dict] = {}
    for submission in submissions:
        management_review = mgmt_lookup.get(submission["id"])
        owner_review = owner_lookup.get(submission["id"])
        if not management_review and not owner_review:
            continue
        key = (submission.get("crew_label") or submission.get("truck_number"), submission.get("service_type") or "unspecified")
        entry = heatmap_tracker.setdefault(
            key,
            {
                "crew": key[0],
                "service_type": key[1],
                "management_scores": [],
                "owner_scores": [],
                "variances": [],
            },
        )
        if management_review:
            entry["management_scores"].append(management_review.get("total_score", 0))
        if owner_review:
            entry["owner_scores"].append(owner_review.get("total_score", 0))
        if management_review and owner_review:
            entry["variances"].append(owner_review.get("variance_from_management", 0))

    calibration_heatmap = []
    for entry in heatmap_tracker.values():
        calibration_heatmap.append(
            {
                "crew": entry["crew"],
                "service_type": entry["service_type"],
                "management_average": round(sum(entry["management_scores"]) / max(len(entry["management_scores"]), 1), 1),
                "owner_average": round(sum(entry["owner_scores"]) / max(len(entry["owner_scores"]), 1), 1),
                "variance_average": round(sum(entry["variances"]) / max(len(entry["variances"]), 1), 1),
                "sample_count": max(len(entry["management_scores"]), len(entry["owner_scores"])),
            }
        )

    return {
        "average_score_by_crew": average_by_crew,
        "score_variance_average": variance_avg,
        "fail_reason_frequency": [{"reason": key, "count": value} for key, value in fail_reasons.items()],
        "submission_volume_trends": [{"day": key, "count": value} for key, value in sorted(volume_by_day.items())],
        "training_approved_count": len([review for review in owner_reviews if review["training_inclusion"] == "approved"]),
        "calibration_heatmap": calibration_heatmap,
    }


def build_export_rows(submissions: list[dict], management_lookup: dict, owner_lookup: dict) -> list[dict]:
    rows = []
    for submission in submissions:
        management_review = management_lookup.get(submission["id"], {})
        owner_review = owner_lookup.get(submission["id"], {})
        rows.append(
            {
                "submission_id": submission["id"],
                "submission_code": submission["submission_code"],
                "job_id": submission.get("job_id"),
                "job_name_input": submission.get("job_name_input"),
                "matched_job_id": submission.get("matched_job_id"),
                "crew_label": submission.get("crew_label"),
                "truck_number": submission.get("truck_number"),
                "division": submission.get("division"),
                "service_type": submission.get("service_type"),
                "status": submission.get("status"),
                "captured_at": submission.get("captured_at"),
                "gps_lat": submission.get("gps", {}).get("lat"),
                "gps_lng": submission.get("gps", {}).get("lng"),
                "photo_urls": json.dumps([item.get("media_url") for item in submission.get("photo_files", [])]),
                "field_report_type": submission.get("field_report", {}).get("type"),
                "field_report_notes": submission.get("field_report", {}).get("notes"),
                "field_report_photo_urls": json.dumps([
                    item.get("media_url") for item in submission.get("field_report", {}).get("photo_files", [])
                ]),
                "management_total_score": management_review.get("total_score"),
                "management_disposition": management_review.get("disposition"),
                "owner_total_score": owner_review.get("total_score"),
                "owner_disposition": owner_review.get("final_disposition"),
                "training_inclusion": owner_review.get("training_inclusion"),
                "variance_from_management": owner_review.get("variance_from_management"),
            }
        )
    return rows


@api_router.post("/exports/run")
async def run_export(payload: ExportRunRequest, user: dict = Depends(require_roles("management", "owner"))):
    submissions = await db.submissions.find({}, {"_id": 0}).to_list(5000)
    management_reviews = await db.management_reviews.find({}, {"_id": 0}).to_list(5000)
    owner_reviews = await db.owner_reviews.find({}, {"_id": 0}).to_list(5000)
    management_lookup = {review["submission_id"]: review for review in management_reviews}
    owner_lookup = {review["submission_id"]: review for review in owner_reviews}

    if payload.dataset_type == "owner_gold":
        submissions = [item for item in submissions if owner_lookup.get(item["id"], {}).get("training_inclusion") == "approved"]

    rows = build_export_rows(submissions, management_lookup, owner_lookup)
    export_id = make_id("export")
    extension = "jsonl" if payload.export_format == "jsonl" else "csv"
    export_path = EXPORTS_DIR / f"{export_id}.{extension}"

    if payload.export_format == "jsonl":
        export_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    else:
        with export_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()) if rows else ["submission_id"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    record = {
        "id": export_id,
        "dataset_type": payload.dataset_type,
        "export_format": payload.export_format,
        "row_count": len(rows),
        "file_path": str(export_path),
        "requested_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], "Dataset export generated")],
    }
    await db.export_records.insert_one({**record})
    await db.submissions.update_many(
        {"id": {"$in": [row["submission_id"] for row in rows]}},
        {
            "$set": {"last_exported_at": now_iso(), "last_export_id": export_id, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("dataset_exported", user["id"], export_id)},
        },
    )
    return record


@api_router.get("/exports")
async def get_exports(user: dict = Depends(require_roles("management", "owner"))):
    return await db.export_records.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api_router.get("/exports/{export_id}/download")
async def download_export(export_id: str, user: dict = Depends(require_roles("management", "owner"))):
    export_record = await db.export_records.find_one({"id": export_id}, {"_id": 0})
    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(export_record["file_path"], filename=Path(export_record["file_path"]).name)


@api_router.get("/integrations/drive/status")
async def drive_status(user: dict = Depends(require_roles("management", "owner"))):
    credentials_count = await db.drive_credentials.count_documents({})
    return {
        "configured": is_drive_configured(),
        "connected": credentials_count > 0,
        "required_env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_DRIVE_REDIRECT_URI"],
        "scope": SCOPES,
    }


@api_router.get("/integrations/drive/connect")
async def connect_drive(user: dict = Depends(require_roles("management", "owner"))):
    if not is_drive_configured():
        raise HTTPException(status_code=400, detail="Google Drive env configuration is missing")
    return {"authorization_url": get_authorization_url(user["id"]) }


@api_router.get("/oauth/drive/callback")
async def drive_callback(code: str, state: str):
    if not is_drive_configured():
        raise HTTPException(status_code=400, detail="Google Drive env configuration is missing")
    flow = build_oauth_flow(state)
    flow.fetch_token(code=code)
    credentials = flow.credentials
    granted_scopes = set(credentials.scopes or [])
    if not set(SCOPES).issubset(granted_scopes):
        raise HTTPException(status_code=400, detail="Missing required Google Drive scope")
    document = credentials_to_document(credentials, state)
    await db.drive_credentials.update_many({}, {"$set": {"is_active": False}})
    await db.drive_credentials.update_one({"user_id": state}, {"$set": document}, upsert=True)
    return {"redirect": f"{os.environ['FRONTEND_URL']}/settings?drive_connected=true"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
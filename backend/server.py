import asyncio
import csv
import html
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
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from supabase import Client, create_client

from shared.models import (
    CrewAccessCreate,
    CrewAccessUpdate,
    CrewLinkStatusUpdateRequest,
    ExportRunRequest,
    LoginRequest,
    ManagementReviewRequest,
    MatchOverrideRequest,
    OwnerReviewRequest,
    RapidReviewRequest,
    RapidReviewSessionEnd,
    RapidReviewSessionStart,
    RubricCategoryInput,
    RubricMatrixCreate,
    RubricMatrixUpdate,
    StandardItemRequest,
    StandardItemUpdateRequest,
    TrainingAnswerSubmission,
    TrainingSessionCreateRequest,
    TrainingSessionSubmitRequest,
    UserCreateRequest,
    UserStatusUpdateRequest,
)
from starlette.middleware.cors import CORSMiddleware

from auth_utils import create_access_token, decode_access_token, get_password_hash, verify_password


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
supabase_client: Client | None = None
ANALYTICS_PERIODS = {
    "daily": {"days": 1, "label": "Daily"},
    "weekly": {"days": 7, "label": "Weekly"},
    "monthly": {"days": 30, "label": "Monthly"},
    "quarterly": {"days": 90, "label": "Quarterly"},
    "annual": {"days": 365, "label": "Annual"},
}
RAPID_REVIEW_RATING_MULTIPLIERS = {
    "fail": 0.2,
    "concern": 0.55,
    "standard": 0.82,
    "exemplary": 1.0,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utc_now().isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def dump_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


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


def normalize_page(page: int) -> int:
    return max(page, 1)


def normalize_limit(limit: int, default: int = 10, max_limit: int = 100) -> int:
    if not limit:
        return default
    return max(1, min(limit, max_limit))


def build_paginated_response(items: list[dict], page: int, limit: int, total: int) -> dict:
    total_pages = max(math.ceil(total / max(limit, 1)), 1) if total else 1
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


def storage_is_configured() -> bool:
    return all(
        os.environ.get(key)
        for key in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "STORAGE_BUCKET_SUBMISSIONS"]
    )


def get_storage_bucket() -> str:
    return os.environ["STORAGE_BUCKET_SUBMISSIONS"]


def get_storage_status_payload() -> dict:
    configured = storage_is_configured()
    return {
        "provider": "supabase",
        "label": "Supabase Storage",
        "configured": configured,
        "connected": configured,
        "bucket": os.environ.get("STORAGE_BUCKET_SUBMISSIONS"),
        "project_url": os.environ.get("SUPABASE_URL"),
        "required_env": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "STORAGE_BUCKET_SUBMISSIONS"],
        "mode": "backend-managed service role",
    }


def get_supabase_client() -> Client:
    global supabase_client
    if supabase_client is None:
        supabase_client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    return supabase_client


async def upload_bytes_to_storage(path: str, content: bytes, content_type: str, bucket: str | None = None) -> None:
    bucket_name = bucket or get_storage_bucket()

    def _upload() -> None:
        get_supabase_client().storage.from_(bucket_name).upload(
            path,
            content,
            {"content-type": content_type, "upsert": "false"},
        )

    await asyncio.to_thread(_upload)


async def download_bytes_from_storage(path: str, bucket: str | None = None) -> bytes:
    bucket_name = bucket or get_storage_bucket()
    return await asyncio.to_thread(lambda: get_supabase_client().storage.from_(bucket_name).download(path))


def build_storage_path(submission_id: str, folder: str, filename: str) -> str:
    return f"sarver-landscape/submissions/{submission_id}/{folder}/{filename}"


def build_submission_file_response_url(submission_id: str, filename: str) -> tuple[str, str]:
    relative_api_path = f"/api/submissions/files/{submission_id}/{filename}"
    return relative_api_path, f"{os.environ['FRONTEND_URL']}{relative_api_path}"


def build_equipment_file_response_url(log_id: str, filename: str) -> tuple[str, str]:
    relative_api_path = f"/api/equipment-logs/files/{log_id}/{filename}"
    return relative_api_path, f"{os.environ['FRONTEND_URL']}{relative_api_path}"


def build_missing_image_placeholder(filename: str) -> bytes:
    safe_name = html.escape(filename)
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='1200' height='800' viewBox='0 0 1200 800'>
      <rect width='1200' height='800' fill='#edf0e7'/>
      <rect x='70' y='70' width='1060' height='660' rx='36' fill='#d8e4da' stroke='#b8c5ba' stroke-width='4'/>
      <text x='600' y='350' text-anchor='middle' font-size='42' fill='#243e36' font-family='Arial, sans-serif'>Image temporarily unavailable</text>
      <text x='600' y='410' text-anchor='middle' font-size='24' fill='#5c6d64' font-family='Arial, sans-serif'>{safe_name}</text>
    </svg>
    """.strip()
    return svg.encode("utf-8")


def hydrate_submission_media(submission: dict | None) -> dict | None:
    if not submission:
        return None
    hydrated = {**submission}

    def hydrate_file_entry(entry: dict) -> dict:
        item = {**entry}
        if item.get("source_type") in {"supabase", "local"} and item.get("filename"):
            relative_api_path, media_url = build_submission_file_response_url(hydrated["id"], item["filename"])
            item["relative_api_path"] = relative_api_path
            item["media_url"] = media_url
        return item

    hydrated["photo_files"] = [hydrate_file_entry(item) for item in submission.get("photo_files", [])]
    if submission.get("field_report"):
        field_report = {**submission["field_report"]}
        field_report["photo_files"] = [
            hydrate_file_entry(item) for item in submission.get("field_report", {}).get("photo_files", [])
        ]
        hydrated["field_report"] = field_report
    return hydrated


def find_submission_file_entry(submission: dict, filename: str) -> dict | None:
    for item in submission.get("photo_files", []):
        if item.get("filename") == filename:
            return item
    for item in submission.get("field_report", {}).get("photo_files", []):
        if item.get("filename") == filename:
            return item
    return None


def get_submission_list_projection() -> dict:
    return {
        "_id": 0,
        "id": 1,
        "submission_code": 1,
        "job_id": 1,
        "job_name_input": 1,
        "crew_label": 1,
        "truck_number": 1,
        "division": 1,
        "service_type": 1,
        "task_type": 1,
        "status": 1,
        "match_status": 1,
        "match_confidence": 1,
        "created_at": 1,
    }


def get_jobs_projection() -> dict:
    return {
        "_id": 0,
        "id": 1,
        "job_id": 1,
        "job_name": 1,
        "property_name": 1,
        "address": 1,
        "service_type": 1,
        "scheduled_date": 1,
        "division": 1,
        "truck_number": 1,
        "route": 1,
    }


def get_crew_link_projection() -> dict:
    return {
        "_id": 0,
        "id": 1,
        "code": 1,
        "crew_member_id": 1,
        "label": 1,
        "truck_number": 1,
        "division": 1,
        "assignment": 1,
        "enabled": 1,
        "created_at": 1,
        "updated_at": 1,
    }


def get_period_cutoff(period: str) -> datetime:
    config = ANALYTICS_PERIODS.get(period, ANALYTICS_PERIODS["monthly"])
    return utc_now() - timedelta(days=config["days"])


def get_period_bucket(dt: datetime, period: str) -> tuple[datetime, str]:
    if period == "daily":
        bucket_start = dt.replace(minute=0, second=0, microsecond=0)
        label = bucket_start.strftime("%H:%M")
    elif period == "weekly":
        bucket_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        label = bucket_start.strftime("%b %d")
    elif period == "monthly":
        bucket_start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        label = f"Week of {bucket_start.strftime('%b %d')}"
    else:
        bucket_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = bucket_start.strftime("%b %Y")
    return bucket_start, label


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




RUBRIC_LIBRARY = [
    {
        "id": "rubric_bed_edging_v1",
        "service_type": "bed edging",
        "division": "Maintenance",
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
        "division": "Maintenance",
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
        "division": "Maintenance",
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
    {
        "id": "rubric_property_maintenance_v1",
        "service_type": "property maintenance",
        "division": "Maintenance",
        "title": "Property Maintenance v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 80,
        "hard_fail_conditions": ["unsafe_site_left", "major_missed_scope"],
        "categories": [
            {"key": "horticultural_quality", "label": "Horticultural Quality", "weight": 0.34, "max_score": 5},
            {"key": "scope_completeness", "label": "Scope Completeness", "weight": 0.33, "max_score": 5},
            {"key": "site_finish", "label": "Site Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_pruning_v1",
        "service_type": "pruning",
        "division": "Maintenance",
        "title": "Pruning v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 82,
        "hard_fail_conditions": ["plant_damage", "unsafe_cutting_practice"],
        "categories": [
            {"key": "cut_quality", "label": "Cut Quality", "weight": 0.34, "max_score": 5},
            {"key": "shape_intent", "label": "Shape Intent", "weight": 0.33, "max_score": 5},
            {"key": "cleanup_finish", "label": "Cleanup Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_weeding_v1",
        "service_type": "weeding",
        "division": "Maintenance",
        "title": "Weeding v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 80,
        "hard_fail_conditions": ["weed_patch_missed", "ornamental_damage"],
        "categories": [
            {"key": "weed_removal", "label": "Weed Removal", "weight": 0.34, "max_score": 5},
            {"key": "bed_protection", "label": "Bed Protection", "weight": 0.33, "max_score": 5},
            {"key": "final_cleanup", "label": "Final Cleanup", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_mulching_v1",
        "service_type": "mulching",
        "division": "Maintenance",
        "title": "Mulching v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 82,
        "hard_fail_conditions": ["mulch_on_turf", "root_flare_buried"],
        "categories": [
            {"key": "depth_consistency", "label": "Depth Consistency", "weight": 0.34, "max_score": 5},
            {"key": "bed_definition", "label": "Bed Definition", "weight": 0.33, "max_score": 5},
            {"key": "spill_control", "label": "Spill Control", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_softscape_v1",
        "service_type": "softscape",
        "division": "Install",
        "title": "Softscape v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 83,
        "hard_fail_conditions": ["material_damage", "layout_miss"],
        "categories": [
            {"key": "layout_accuracy", "label": "Layout Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "material_condition", "label": "Material Condition", "weight": 0.33, "max_score": 5},
            {"key": "finish_detail", "label": "Finish Detail", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_hardscape_v1",
        "service_type": "hardscape",
        "division": "Install",
        "title": "Hardscape v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 84,
        "hard_fail_conditions": ["trip_hazard", "failed_alignment"],
        "categories": [
            {"key": "alignment_grade", "label": "Alignment / Grade", "weight": 0.34, "max_score": 5},
            {"key": "stability_compaction", "label": "Stability / Compaction", "weight": 0.33, "max_score": 5},
            {"key": "finish_detail", "label": "Finish Detail", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_tree_plant_install_removal_v1",
        "service_type": "tree/plant install/removal",
        "division": "Install",
        "title": "Tree/Plant Install/Removal v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 82,
        "hard_fail_conditions": ["unsafe_lift", "site_damage"],
        "categories": [
            {"key": "safety_control", "label": "Safety / Control", "weight": 0.34, "max_score": 5},
            {"key": "plant_material_handling", "label": "Plant/Material Handling", "weight": 0.33, "max_score": 5},
            {"key": "site_restoration", "label": "Site Restoration", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_drainage_trenching_v1",
        "service_type": "drainage/trenching",
        "division": "Install",
        "title": "Drainage/Trenching v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 82,
        "hard_fail_conditions": ["poor_grade", "unsafe_open_trench"],
        "categories": [
            {"key": "trench_accuracy", "label": "Trench Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "drainage_function", "label": "Drainage Function", "weight": 0.33, "max_score": 5},
            {"key": "restoration_finish", "label": "Restoration Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_lighting_v1",
        "service_type": "lighting",
        "division": "Install",
        "title": "Lighting v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["wiring_exposed", "fixture_misfire"],
        "categories": [
            {"key": "placement_accuracy", "label": "Placement Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "function_test", "label": "Function Test", "weight": 0.33, "max_score": 5},
            {"key": "concealment_finish", "label": "Concealment Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_removal_v1",
        "service_type": "removal",
        "division": "Tree",
        "title": "Removal v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 84,
        "hard_fail_conditions": ["unsafe_drop_zone", "debris_left_behind"],
        "categories": [
            {"key": "safety_execution", "label": "Safety Execution", "weight": 0.34, "max_score": 5},
            {"key": "debris_clearance", "label": "Debris Clearance", "weight": 0.33, "max_score": 5},
            {"key": "surface_protection", "label": "Surface Protection", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_stump_grinding_v1",
        "service_type": "stump grinding",
        "division": "Tree",
        "title": "Stump Grinding v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["stump_remaining", "surface_damage"],
        "categories": [
            {"key": "grind_completeness", "label": "Grind Completeness", "weight": 0.34, "max_score": 5},
            {"key": "debris_containment", "label": "Debris Containment", "weight": 0.33, "max_score": 5},
            {"key": "surface_finish", "label": "Surface Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_fert_and_chem_treatments_v1",
        "service_type": "fert and chem treatments",
        "division": "Plant Healthcare",
        "title": "Fert and Chem Treatments v1",
        "version": 1,
        "min_photos": 2,
        "pass_threshold": 85,
        "hard_fail_conditions": ["label_noncompliance", "unsafe_application"],
        "categories": [
            {"key": "coverage_accuracy", "label": "Coverage Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "safety_compliance", "label": "Safety Compliance", "weight": 0.33, "max_score": 5},
            {"key": "record_clarity", "label": "Record Clarity", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_air_spade_v1",
        "service_type": "air spade",
        "division": "Plant Healthcare",
        "title": "Air Spade v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["root_damage", "unsafe_excavation"],
        "categories": [
            {"key": "root_zone_care", "label": "Root Zone Care", "weight": 0.34, "max_score": 5},
            {"key": "excavation_control", "label": "Excavation Control", "weight": 0.33, "max_score": 5},
            {"key": "restoration_finish", "label": "Restoration Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_dormant_pruning_v1",
        "service_type": "dormant pruning",
        "division": "Plant Healthcare",
        "title": "Dormant Pruning v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["bud_damage", "unsafe_cutting_practice"],
        "categories": [
            {"key": "pruning_intent", "label": "Pruning Intent", "weight": 0.34, "max_score": 5},
            {"key": "plant_health_protection", "label": "Plant Health Protection", "weight": 0.33, "max_score": 5},
            {"key": "cleanup_finish", "label": "Cleanup Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_deer_fencing_and_shrub_treatment_v1",
        "service_type": "deer fencing and shrub treatment",
        "division": "Plant Healthcare",
        "title": "Deer Fencing and Shrub Treatment v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["coverage_gap", "plant_damage"],
        "categories": [
            {"key": "protection_coverage", "label": "Protection Coverage", "weight": 0.34, "max_score": 5},
            {"key": "treatment_quality", "label": "Treatment Quality", "weight": 0.33, "max_score": 5},
            {"key": "final_presentation", "label": "Final Presentation", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_snow_removal_v1",
        "service_type": "snow removal",
        "division": "Winter Services",
        "title": "Snow Removal v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 85,
        "hard_fail_conditions": ["unsafe_walkway", "missed_access_lane"],
        "categories": [
            {"key": "surface_coverage", "label": "Surface Coverage", "weight": 0.34, "max_score": 5},
            {"key": "access_safety", "label": "Access Safety", "weight": 0.33, "max_score": 5},
            {"key": "pile_placement", "label": "Pile Placement", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_plow_v1",
        "service_type": "plow",
        "division": "Winter Services",
        "title": "Plow v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["missed_route", "curb_damage"],
        "categories": [
            {"key": "route_completeness", "label": "Route Completeness", "weight": 0.34, "max_score": 5},
            {"key": "obstruction_control", "label": "Obstruction Control", "weight": 0.33, "max_score": 5},
            {"key": "final_surface", "label": "Final Surface", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_salting_v1",
        "service_type": "salting",
        "division": "Winter Services",
        "title": "Salting v1",
        "version": 1,
        "min_photos": 2,
        "pass_threshold": 85,
        "hard_fail_conditions": ["untreated_hazard_zone", "material_overuse"],
        "categories": [
            {"key": "coverage_consistency", "label": "Coverage Consistency", "weight": 0.34, "max_score": 5},
            {"key": "slip_risk_reduction", "label": "Slip-Risk Reduction", "weight": 0.33, "max_score": 5},
            {"key": "material_control", "label": "Material Control", "weight": 0.33, "max_score": 5},
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
            "Supabase Storage service layer for proof images and review-ready asset retrieval",
        ],
        "storage": [
            "Supabase bucket-backed image storage managed by the backend service role",
            "Stable backend-served image routes for admin and owner review screens",
            "Export bundle generation for JSONL and CSV",
        ],
    },
    "database_schema": [
        "jobs",
        "submissions",
        "rapid_reviews",
        "standards_library",
        "training_sessions",
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
    rapid_review = await db.rapid_reviews.find_one({"submission_id": submission_id}, {"_id": 0})
    job = None
    if submission.get("matched_job_id"):
        job = await db.jobs.find_one({"id": submission["matched_job_id"]}, {"_id": 0})
    rubric = None
    if submission.get("service_type"):
        rubric = await db.rubric_definitions.find_one(
            {"service_type": submission["service_type"].lower(), "is_active": True}, {"_id": 0}, sort=[("version", -1)]
        )
    return {
        "submission": hydrate_submission_media(submission),
        "management_review": management_review,
        "owner_review": owner_review,
        "rapid_review": rapid_review,
        "job": job,
        "rubric": rubric,
    }


def calculate_rapid_review_score_summary(rubric: dict, overall_rating: str) -> dict:
    total_weighted_points = sum(category["weight"] for category in rubric.get("categories", []))
    normalized_percent = round(total_weighted_points * RAPID_REVIEW_RATING_MULTIPLIERS[overall_rating] * 100, 1)
    return {
        "overall_rating": overall_rating,
        "rubric_sum_percent": normalized_percent,
        "multiplier": RAPID_REVIEW_RATING_MULTIPLIERS[overall_rating],
    }


async def build_rapid_review_queue(page: int, limit: int) -> dict:
    reviewed_submission_ids = await db.rapid_reviews.distinct("submission_id", {})
    query: dict[str, Any] = {
        "service_type": {"$ne": ""},
        "status": {"$in": ["Ready for Review", "Management Reviewed", "Owner Reviewed", "Export Ready"]},
    }
    if reviewed_submission_ids:
        query["id"] = {"$nin": reviewed_submission_ids}
    total = await db.submissions.count_documents(query)
    items = (
        await db.submissions.find(query, get_submission_list_projection())
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


def match_training_answer(correct_answer: str, response: str) -> bool:
    accepted_values = [item.strip().lower() for item in correct_answer.split("|") if item.strip()]
    normalized_response = response.strip().lower()
    return normalized_response in accepted_values if accepted_values else False


def calculate_repeat_offender_level(count: int, thresholds: tuple[int, int, int]) -> str:
    level_one, level_two, level_three = thresholds
    if count >= level_three:
        return "Level 3: Supervisor Review"
    if count >= level_two:
        return "Level 2: Training Required"
    if count >= level_one:
        return "Level 1: Warning"
    return "Monitor"


async def build_repeat_offender_summary(days: int, thresholds: tuple[int, int, int]) -> dict:
    cutoff = (utc_now() - timedelta(days=days)).isoformat()
    submissions = await db.submissions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "id": 1, "crew_label": 1, "access_code": 1, "division": 1, "job_name_input": 1, "job_id": 1, "field_report": 1, "created_at": 1},
    ).to_list(5000)
    submission_lookup = {item["id"]: item for item in submissions}
    by_crew: dict[str, dict] = {}
    heatmap: dict[tuple[str, str], dict] = {}

    def register_event(submission_id: str, issue_type: str, source: str) -> None:
        submission = submission_lookup.get(submission_id)
        if not submission:
            return
        crew_key = submission.get("crew_label") or "Unknown Crew"
        crew_entry = by_crew.setdefault(
            crew_key,
            {
                "crew": crew_key,
                "access_code": submission.get("access_code", ""),
                "division": submission.get("division", ""),
                "incident_count": 0,
                "issue_types": {},
                "submission_ids": [],
                "related_submissions": [],
            },
        )
        crew_entry["incident_count"] += 1
        crew_entry["issue_types"][issue_type] = crew_entry["issue_types"].get(issue_type, 0) + 1
        if submission_id not in crew_entry["submission_ids"]:
            crew_entry["submission_ids"].append(submission_id)
            crew_entry["related_submissions"].append(
                {
                    "submission_id": submission_id,
                    "label": submission.get("job_name_input") or submission.get("job_id") or submission_id,
                    "created_at": submission.get("created_at"),
                    "source": source,
                }
            )
        cell_key = (crew_key, issue_type)
        cell = heatmap.setdefault(
            cell_key,
            {
                "crew": crew_key,
                "issue_type": issue_type,
                "count": 0,
                "submission_ids": [],
            },
        )
        cell["count"] += 1
        if submission_id not in cell["submission_ids"]:
            cell["submission_ids"].append(submission_id)

    rapid_reviews = await db.rapid_reviews.find(
        {"created_at": {"$gte": cutoff}, "overall_rating": {"$in": ["fail", "concern"]}},
        {"_id": 0, "submission_id": 1, "issue_tag": 1, "overall_rating": 1},
    ).to_list(5000)
    for review in rapid_reviews:
        register_event(review["submission_id"], review.get("issue_tag") or review.get("overall_rating") or "rapid_review", "rapid_review")

    management_reviews = await db.management_reviews.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "submission_id": 1, "flagged_issues": 1, "disposition": 1},
    ).to_list(5000)
    for review in management_reviews:
        if review.get("disposition") and review["disposition"] != "pass":
            register_event(review["submission_id"], review["disposition"], "management_review")
        for issue in review.get("flagged_issues", []):
            register_event(review["submission_id"], issue, "management_review")

    for submission in submissions:
        field_report = submission.get("field_report") or {}
        if field_report.get("reported"):
            register_event(submission["id"], field_report.get("type") or "field_report", "field_report")

    crew_summaries = []
    for entry in by_crew.values():
        entry["level"] = calculate_repeat_offender_level(entry["incident_count"], thresholds)
        entry["top_issue_type"] = max(entry["issue_types"], key=entry["issue_types"].get) if entry["issue_types"] else ""
        crew_summaries.append(entry)
    crew_summaries.sort(key=lambda item: item["incident_count"], reverse=True)

    heatmap_rows = list(heatmap.values())
    for row in heatmap_rows:
        crew_count = next((item["incident_count"] for item in crew_summaries if item["crew"] == row["crew"]), 0)
        row["level"] = calculate_repeat_offender_level(crew_count, thresholds)
    heatmap_rows.sort(key=lambda item: (item["crew"], -item["count"], item["issue_type"]))

    return {
        "window_days": days,
        "thresholds": {"level_1": thresholds[0], "level_2": thresholds[1], "level_3": thresholds[2]},
        "crew_summaries": crew_summaries,
        "heatmap": heatmap_rows,
    }


async def get_recent_training_sessions(page: int, limit: int) -> dict:
    total = await db.training_sessions.count_documents({})
    items = (
        await db.training_sessions.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


async def select_training_snapshots(division: str, item_count: int) -> list[dict]:
    standards = await db.standards_library.find({"is_active": True, "training_enabled": True}, {"_id": 0}).sort("created_at", -1).to_list(200)
    eligible = [
        item for item in standards
        if item.get("audience") in {"crew", "both"}
        and (not division or not item.get("division_targets") or division in item.get("division_targets", []))
    ]
    return eligible[:item_count]


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
        {"name": "Johnny H", "email": "HJohnny.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Craig S", "email": "SCraig.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Fran P", "email": "PFran.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Scott K", "email": "KScott.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Megan B", "email": "BMegan.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Daniel M", "email": "MDaniel.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Tim A", "email": "ATim.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Zach O", "email": "OZach.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Scott W", "email": "WScott.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Tyler C", "email": "CTyler.GM@SLMCo.local", "role": "management", "title": "GM"},
        {"name": "Brad S", "email": "SBrad.GM@SLMCo.local", "role": "management", "title": "GM"},
        {"name": "Adam S", "email": "SAdam.Owner@SLMCo.local", "role": "owner", "title": "Owner"},
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
                    "password_hash": get_password_hash("SLMCo2026!"),
                    "is_active": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", f"{user['title']} demo account created")],
                }
            )

    await db.jobs.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.crew_access_links.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.submissions.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})

    for rubric in RUBRIC_LIBRARY:
        existing = await db.rubric_definitions.find_one({"service_type": rubric["service_type"].lower(), "version": rubric["version"]}, {"_id": 0})
        document = {
            **rubric,
            "service_type": rubric["service_type"].lower(),
            "is_active": True,
            "created_at": existing.get("created_at", now_iso()) if existing else now_iso(),
            "updated_at": now_iso(),
            "audit_history": existing.get("audit_history", [audit_entry("seeded", "system", f"Rubric {rubric['title']} loaded")]) if existing else [audit_entry("seeded", "system", f"Rubric {rubric['title']} loaded")],
        }
        await db.rubric_definitions.update_one(
            {"service_type": rubric["service_type"].lower(), "version": rubric["version"]},
            {"$set": document},
            upsert=True,
        )

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
                    "storage_status": "seed_remote",
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
                    "storage_status": "seed_remote",
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
                    "storage_status": "seed_remote",
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

    if await db.standards_library.count_documents({}) == 0:
        standards = [
            {
                "id": make_id("std"),
                "title": "Clean bed edge finish",
                "category": "Edging",
                "audience": "crew",
                "division_targets": ["Maintenance", "Install"],
                "checklist": ["Edge line reads clean", "No turf spill", "Street-facing finish shot included"],
                "notes": "Use one wide establishing shot and one close-up of the edge line.",
                "owner_notes": "Great baseline example for edging crews.",
                "shoutout": "@North Crew",
                "image_url": "https://images.unsplash.com/photo-1734303023491-db8037a21f09?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "Which result best matches this standard?",
                "choice_options": ["Street-ready edge", "Needs more cleanup", "Unsafe site"],
                "correct_answer": "Street-ready edge",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Mulch bed cleanliness",
                "category": "Mulch",
                "audience": "crew",
                "division_targets": ["Install", "Maintenance"],
                "checklist": ["Mulch kept out of turf", "Bed edge visible", "Depth looks even"],
                "notes": "Capture texture and edge definition together.",
                "owner_notes": "Use for install coaching when edges are lost.",
                "shoutout": "@Install Team",
                "image_url": "https://images.pexels.com/photos/30467599/pexels-photo-30467599.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "What should a reviewer confirm first?",
                "choice_options": ["Depth consistency", "Truck number", "Weather"],
                "correct_answer": "Depth consistency",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Cleanup completion proof",
                "category": "Cleanup",
                "audience": "crew",
                "division_targets": ["Maintenance", "PHC - Plant Healthcare"],
                "checklist": ["Debris removed", "Walks clear", "Final condition is obvious"],
                "notes": "Use a final shot that clearly proves the reset is complete.",
                "owner_notes": "Best used for spring/fall cleanups.",
                "shoutout": "@Cleanup Team",
                "image_url": "https://images.unsplash.com/photo-1734079692160-fcbe4be6ab96?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "free_text",
                "question_prompt": "In one phrase, what makes this proof set feel complete?",
                "choice_options": [],
                "correct_answer": "clear final condition|final condition is obvious|complete reset",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Tree pruning clarity",
                "category": "Pruning",
                "audience": "crew",
                "division_targets": ["Sarver Tree"],
                "checklist": ["Cut area visible", "Safety zone clear", "Final canopy view shown"],
                "notes": "Always show both the cut detail and the cleared zone.",
                "owner_notes": "Tree division standard example.",
                "shoutout": "@Tree Crew",
                "image_url": "https://images.unsplash.com/photo-1772764057845-121fd5f3ebe8?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "Which extra image should always be included with pruning work?",
                "choice_options": ["Safety zone clear shot", "Truck dashboard", "Sky only"],
                "correct_answer": "Safety zone clear shot",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        ]
        await db.standards_library.insert_many(standards)


@app.on_event("startup")
async def startup_event():
    await seed_defaults()
    await db.rapid_reviews.create_index("submission_id", unique=True)
    await db.rapid_review_sessions.create_index("reviewer_id")
    await db.rapid_review_sessions.create_index("created_at")
    await db.standards_library.create_index("id", unique=True)
    await db.training_sessions.create_index("code", unique=True)
    if storage_is_configured():
        try:
            get_supabase_client()
            logger.info("Supabase storage client initialized")
        except Exception as exc:
            logger.error("Supabase storage initialization failed: %s", exc)


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
    request: Request,
    access_code: str = Form(...),
    job_id: str = Form(""),
    job_name: str = Form(""),
    task_type: str = Form(""),
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
        relative_api_path, media_url = build_submission_file_response_url(submission_id, filename)
        storage_path = build_storage_path(submission_id, "captures", filename)
        await upload_bytes_to_storage(storage_path, content, photo.content_type or "application/octet-stream")
        photo_files.append(
            {
                "id": make_id("file"),
                "filename": filename,
                "original_name": photo.filename,
                "mime_type": photo.content_type or "application/octet-stream",
                "sequence": index,
                "size_bytes": len(content),
                "bucket": get_storage_bucket(),
                "storage_path": storage_path,
                "relative_api_path": relative_api_path,
                "media_url": media_url,
                "source_type": "supabase",
            }
        )

    field_report_photo_files = []
    for index, issue_photo in enumerate(issue_photos or [], start=1):
        content = await issue_photo.read()
        suffix = Path(issue_photo.filename or f"issue-{index}.jpg").suffix or ".jpg"
        filename = f"issue_{index:02d}_{uuid.uuid4().hex[:6]}{suffix}"
        relative_api_path, media_url = build_submission_file_response_url(submission_id, filename)
        storage_path = build_storage_path(submission_id, "issues", filename)
        await upload_bytes_to_storage(storage_path, content, issue_photo.content_type or "application/octet-stream")
        field_report_photo_files.append(
            {
                "id": make_id("issuefile"),
                "filename": filename,
                "original_name": issue_photo.filename,
                "mime_type": issue_photo.content_type or "application/octet-stream",
                "sequence": index,
                "size_bytes": len(content),
                "bucket": get_storage_bucket(),
                "storage_path": storage_path,
                "relative_api_path": relative_api_path,
                "media_url": media_url,
                "source_type": "supabase",
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
        "service_type": (job["service_type"] if job else task_type).lower() if (job or task_type) else "",
        "task_type": task_type,
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
        "storage_status": "stored",
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
        target_titles=["Supervisor", "Production Manager", "Account Manager", "GM"],
        related_submission_id=submission_id,
        related_job_id=job_key,
        notification_type="new_submission",
    )
    if submission["field_report"]["reported"]:
        await create_notification(
            title="Crew reported an issue or damage",
            message=f"{crew_link['label']} reported '{issue_type or 'field issue'}' on {job_name_value}.",
            audience="management",
            target_titles=["Supervisor", "Production Manager", "Account Manager", "GM"],
            related_submission_id=submission_id,
            related_job_id=job_key,
            notification_type="field_issue",
        )
    return {"submission": hydrate_submission_media(submission)}


@api_router.get("/submissions/files/{submission_id}/{filename}")
async def get_submission_file(submission_id: str, filename: str):
    submission = await db.submissions.find_one(
        {"id": submission_id},
        {"_id": 0, "id": 1, "photo_files": 1, "field_report": 1},
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    file_entry = find_submission_file_entry(submission, filename)
    if not file_entry:
        raise HTTPException(status_code=404, detail="File not found")
    if file_entry.get("source_type") == "supabase" and file_entry.get("storage_path"):
        try:
            content = await download_bytes_from_storage(
                file_entry["storage_path"],
                file_entry.get("bucket") or get_storage_bucket(),
            )
            return Response(content=content, media_type=file_entry.get("mime_type", "application/octet-stream"))
        except Exception as exc:
            logger.warning("Storage file unavailable for %s/%s: %s", submission_id, filename, exc)
            return Response(content=build_missing_image_placeholder(filename), media_type="image/svg+xml")

    local_path = file_entry.get("local_path")
    if local_path and Path(local_path).exists():
        return FileResponse(local_path, media_type=file_entry.get("mime_type", "application/octet-stream"))

    return Response(content=build_missing_image_placeholder(filename), media_type="image/svg+xml")


@api_router.post("/public/equipment-logs")
async def create_equipment_log(
    request: Request,
    access_code: str = Form(...),
    equipment_number: str = Form(...),
    general_note: str = Form(""),
    red_tag_note: str = Form(""),
    pre_service_photo: UploadFile = File(...),
    post_service_photo: UploadFile = File(...),
):
    crew_link = await db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew access link not found")

    log_id = make_id("equip")
    local_folder = SUBMISSIONS_DIR / log_id
    local_folder.mkdir(parents=True, exist_ok=True)
    photos = []
    for label, upload in [("pre", pre_service_photo), ("post", post_service_photo)]:
        content = await upload.read()
        suffix = Path(upload.filename or f"{label}.jpg").suffix or ".jpg"
        filename = f"{label}_{uuid.uuid4().hex[:6]}{suffix}"
        relative_api_path, media_url = build_equipment_file_response_url(log_id, filename)
        storage_path = f"sarver-landscape/equipment-logs/{log_id}/{filename}"
        await upload_bytes_to_storage(storage_path, content, upload.content_type or "application/octet-stream")
        photos.append(
            {
                "slot": label,
                "filename": filename,
                "mime_type": upload.content_type or "application/octet-stream",
                "bucket": get_storage_bucket(),
                "storage_path": storage_path,
                "relative_api_path": relative_api_path,
                "media_url": media_url,
                "source_type": "supabase",
            }
        )

    log = {
        "id": log_id,
        "access_code": access_code,
        "crew_label": crew_link["label"],
        "truck_number": crew_link["truck_number"],
        "division": crew_link["division"],
        "equipment_number": equipment_number,
        "general_note": general_note,
        "red_tag_note": red_tag_note,
        "photos": photos,
        "status": "red_tag_review" if red_tag_note else "logged",
        "forwarded_to_owner": False,
        "device_metadata": {"user_agent": request.headers.get("user-agent", "unknown")},
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("submitted", access_code, "Equipment maintenance log created")],
    }
    await db.equipment_logs.insert_one({**log})
    await create_notification(
        title="Equipment maintenance record submitted",
        message=f"{crew_link['label']} logged equipment {equipment_number}.",
        audience="management",
        target_titles=["Supervisor", "Production Manager", "Account Manager", "GM"],
        notification_type="equipment_log",
    )
    if red_tag_note:
        await create_notification(
            title="Red-tag equipment issue reported",
            message=f"{crew_link['label']} flagged equipment {equipment_number}: {red_tag_note}",
            audience="management",
            target_titles=["Supervisor", "Production Manager", "GM"],
            notification_type="equipment_red_tag",
        )
    return {"equipment_log": log}


@api_router.get("/equipment-logs")
async def get_equipment_logs(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await db.equipment_logs.count_documents({})
    items = (
        await db.equipment_logs.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@api_router.post("/equipment-logs/{log_id}/forward-to-owner")
async def forward_equipment_log_to_owner(log_id: str, user: dict = Depends(require_roles("management", "owner"))):
    if user.get("title") != "GM" and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only GM or Owner can forward this red-tag to Owner review")
    equipment_log = await db.equipment_logs.find_one({"id": log_id}, {"_id": 0})
    if not equipment_log:
        raise HTTPException(status_code=404, detail="Equipment log not found")
    await db.equipment_logs.update_one(
        {"id": log_id},
        {"$set": {"forwarded_to_owner": True, "updated_at": now_iso()}},
    )
    await create_notification(
        title="Equipment red-tag forwarded to Owner",
        message=f"GM forwarded equipment {equipment_log['equipment_number']} from {equipment_log['crew_label']} for Owner review.",
        audience="owner",
        target_role="owner",
        notification_type="equipment_red_tag_forwarded",
    )
    return {"status": "forwarded"}


@api_router.get("/equipment-logs/files/{log_id}/{filename}")
async def get_equipment_log_file(log_id: str, filename: str):
    equipment_log = await db.equipment_logs.find_one({"id": log_id}, {"_id": 0, "photos": 1})
    if not equipment_log:
        raise HTTPException(status_code=404, detail="Equipment log not found")
    file_entry = next((item for item in equipment_log.get("photos", []) if item.get("filename") == filename), None)
    if not file_entry:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = await download_bytes_from_storage(file_entry["storage_path"], file_entry.get("bucket") or get_storage_bucket())
        return Response(content=content, media_type=file_entry.get("mime_type", "application/octet-stream"))
    except Exception:
        return Response(content=build_missing_image_placeholder(filename), media_type="image/svg+xml")


@api_router.get("/dashboard/overview")
async def get_dashboard_overview(user: dict = Depends(require_roles("management", "owner"))):
    submissions_count = await db.submissions.count_documents({})
    jobs_count = await db.jobs.count_documents({})
    rubrics_count = await db.rubric_definitions.count_documents({})
    export_count = await db.export_records.count_documents({})
    management_queue = await db.submissions.count_documents({"status": {"$in": ["Pending Match", "Ready for Review"]}})
    owner_queue = await db.submissions.count_documents({"status": {"$in": ["Management Reviewed", "Owner Reviewed"]}})
    export_ready = await db.submissions.count_documents({"status": "Export Ready"})
    review_velocity = round((management_queue + owner_queue + export_ready) / max(submissions_count, 1) * 100, 1)
    storage = get_storage_status_payload()
    return {
        "totals": {
            "submissions": submissions_count,
            "jobs": jobs_count,
            "rubrics": rubrics_count,
            "exports": export_count,
        },
        "queues": {
            "management": management_queue,
            "owner": owner_queue,
            "export_ready": export_ready,
        },
        "storage": storage,
        "drive": {"configured": storage["configured"], "connected": storage["connected"], "scope": [storage["bucket"]]},
        "workflow_health": {
            "review_velocity_percent": review_velocity,
            "duplicate_guard_window_minutes": 15,
        },
    }


@api_router.get("/jobs")
async def get_jobs(
    user: dict = Depends(require_roles("management", "owner")),
    search: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    query: dict[str, Any] = {}
    if search:
        query["search_text"] = {"$regex": search.lower()}
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=100)
    total = await db.jobs.count_documents(query)
    jobs = (
        await db.jobs.find(query, get_jobs_projection())
        .sort("scheduled_date", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(jobs, page, limit, total)


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
async def get_crew_access_links(
    user: dict = Depends(require_roles("management", "owner")),
    status: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    query: dict[str, Any] = {}
    if status == "active":
        query["enabled"] = True
    elif status == "inactive":
        query["enabled"] = False
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await db.crew_access_links.count_documents(query)
    crew_links = (
        await db.crew_access_links.find(query, get_crew_link_projection())
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response([present_crew_link(link) for link in crew_links], page, limit, total)


@api_router.post("/crew-access-links")
async def create_crew_access_link(payload: CrewAccessCreate, user: dict = Depends(require_roles("management", "owner"))):
    crew_link = {
        "id": make_id("crew"),
        "code": uuid.uuid4().hex[:8],
        "crew_member_id": make_id("crewid").upper(),
        "label": payload.label,
        "truck_number": payload.truck_number,
        "division": payload.division,
        "assignment": payload.assignment,
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


@api_router.patch("/crew-access-links/{crew_link_id}")
async def update_crew_access_link(
    crew_link_id: str,
    payload: CrewAccessUpdate,
    user: dict = Depends(require_roles("management", "owner")),
):
    await db.crew_access_links.update_one(
        {"id": crew_link_id},
        {
            "$set": {
                "label": payload.label,
                "truck_number": payload.truck_number,
                "division": payload.division,
                "assignment": payload.assignment,
                "updated_at": now_iso(),
            },
            "$push": {"audit_history": audit_entry("updated", user["id"], "Crew QR metadata updated")},
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


@api_router.get("/rubric-matrices")
async def get_rubric_matrices(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = "all",
    service_type: str = "all",
    include_inactive: bool = False,
):
    query: dict[str, Any] = {}
    if not include_inactive:
        query["is_active"] = True
    if division != "all":
        query["division"] = division
    if service_type != "all":
        query["service_type"] = service_type.lower()
    rubrics = await db.rubric_definitions.find(query, {"_id": 0}).sort([("division", 1), ("service_type", 1)]).to_list(200)
    return rubrics


@api_router.post("/rubric-matrices", status_code=201)
async def create_rubric_matrix(
    payload: RubricMatrixCreate,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can create rubric matrices")
    existing = await db.rubric_definitions.find_one(
        {"service_type": payload.service_type.lower(), "division": payload.division, "is_active": True}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Active rubric already exists for {payload.service_type} in {payload.division}")
    max_version_doc = await db.rubric_definitions.find_one(
        {"service_type": payload.service_type.lower()}, {"version": 1, "_id": 0}, sort=[("version", -1)]
    )
    next_version = (max_version_doc["version"] + 1) if max_version_doc else 1
    rubric_id = make_id("rubric")
    document = {
        "id": rubric_id,
        "service_type": payload.service_type.lower(),
        "division": payload.division,
        "title": payload.title,
        "version": next_version,
        "min_photos": payload.min_photos,
        "pass_threshold": payload.pass_threshold,
        "hard_fail_conditions": payload.hard_fail_conditions,
        "categories": [cat.model_dump() for cat in payload.categories],
        "is_active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], f"Rubric matrix created by {user['title']}")],
    }
    await db.rubric_definitions.insert_one(document)
    document.pop("_id", None)
    return document


@api_router.patch("/rubric-matrices/{rubric_id}")
async def update_rubric_matrix(
    rubric_id: str,
    payload: RubricMatrixUpdate,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can update rubric matrices")
    existing = await db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rubric matrix not found")
    updates: dict[str, Any] = {"updated_at": now_iso()}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.division is not None:
        updates["division"] = payload.division
    if payload.min_photos is not None:
        updates["min_photos"] = payload.min_photos
    if payload.pass_threshold is not None:
        updates["pass_threshold"] = payload.pass_threshold
    if payload.hard_fail_conditions is not None:
        updates["hard_fail_conditions"] = payload.hard_fail_conditions
    if payload.categories is not None:
        updates["categories"] = [cat.model_dump() for cat in payload.categories]
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
    await db.rubric_definitions.update_one(
        {"id": rubric_id},
        {
            "$set": updates,
            "$push": {"audit_history": audit_entry("updated", user["id"], f"Rubric updated by {user['title']}")},
        },
    )
    updated = await db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    return serialize(updated)


@api_router.delete("/rubric-matrices/{rubric_id}")
async def delete_rubric_matrix(
    rubric_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can delete rubric matrices")
    existing = await db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rubric matrix not found")
    await db.rubric_definitions.update_one(
        {"id": rubric_id},
        {
            "$set": {"is_active": False, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("deactivated", user["id"], f"Rubric deactivated by {user['title']}")},
        },
    )
    return {"ok": True, "detail": "Rubric matrix deactivated"}


@api_router.get("/standards")
async def get_standards(
    user: dict = Depends(require_roles("management", "owner")),
    search: str = "",
    category: str = "all",
    division: str = "all",
    audience: str = "all",
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
):
    query: dict[str, Any] = {}
    if search:
        query["search_text"] = {"$regex": search.lower()}
    if category != "all":
        query["category"] = category
    if audience != "all":
        query["audience"] = audience
    if division != "all":
        query["$or"] = [{"division_targets": []}, {"division_targets": division}]
    page = normalize_page(page)
    limit = normalize_limit(limit, default=12, max_limit=100)
    total = await db.standards_library.count_documents(query)
    items = (
        await db.standards_library.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@api_router.post("/standards", status_code=201)
async def create_standard_item(payload: StandardItemRequest, user: dict = Depends(require_roles("management", "owner"))):
    document = {
        "id": make_id("std"),
        "title": payload.title,
        "category": payload.category,
        "audience": payload.audience,
        "division_targets": payload.division_targets,
        "checklist": payload.checklist,
        "notes": payload.notes,
        "owner_notes": payload.owner_notes,
        "shoutout": payload.shoutout,
        "image_url": payload.image_url,
        "training_enabled": payload.training_enabled,
        "question_type": payload.question_type,
        "question_prompt": payload.question_prompt,
        "choice_options": payload.choice_options,
        "correct_answer": payload.correct_answer,
        "is_active": payload.is_active,
        "search_text": " ".join([
            payload.title.lower(),
            payload.category.lower(),
            payload.notes.lower(),
            " ".join(item.lower() for item in payload.division_targets),
        ]),
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    response_document = {**document}
    await db.standards_library.insert_one(document)
    return response_document


@api_router.patch("/standards/{standard_id}")
async def update_standard_item(
    standard_id: str,
    payload: StandardItemUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    current = await db.standards_library.find_one({"id": standard_id}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Standard item not found")

    patch_values = payload.model_dump(exclude_none=True)
    merged = {**current, **patch_values}
    update = {
        **patch_values,
        "search_text": " ".join([
            merged["title"].lower(),
            merged["category"].lower(),
            merged.get("notes", "").lower(),
            " ".join(item.lower() for item in merged.get("division_targets", [])),
        ]),
        "updated_at": now_iso(),
        "updated_by": user["id"],
    }
    await db.standards_library.update_one({"id": standard_id}, {"$set": update})
    standard = await db.standards_library.find_one({"id": standard_id}, {"_id": 0})
    return standard


@api_router.get("/repeat-offenders")
async def get_repeat_offenders(
    user: dict = Depends(require_roles("management", "owner")),
    window_days: int = Query(30, ge=1, le=365),
    threshold_one: int = Query(3, ge=1, le=20),
    threshold_two: int = Query(5, ge=1, le=30),
    threshold_three: int = Query(7, ge=1, le=50),
):
    return await build_repeat_offender_summary(window_days, (threshold_one, threshold_two, threshold_three))


@api_router.get("/training-sessions")
async def get_training_sessions(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    return await get_recent_training_sessions(page, limit)


@api_router.post("/training-sessions", status_code=201)
async def create_training_session(
    payload: TrainingSessionCreateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    crew_link = await db.crew_access_links.find_one({"code": payload.access_code}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    division = payload.division or crew_link.get("division", "")
    snapshots = await select_training_snapshots(division, max(1, min(payload.item_count, 5)))
    if not snapshots:
        raise HTTPException(status_code=400, detail="No training-ready standards match this division yet")
    code = f"TRAIN{uuid.uuid4().hex[:8].upper()}"
    session = {
        "id": make_id("train"),
        "code": code,
        "crew_link_id": crew_link["id"],
        "crew_label": crew_link.get("label", "Crew"),
        "access_code": crew_link["code"],
        "division": division,
        "item_count": len(snapshots),
        "items": snapshots,
        "status": "active",
        "score_percent": None,
        "completion_rate": None,
        "average_time_seconds": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    response_session = {**session}
    await db.training_sessions.insert_one(session)
    return {**response_session, "session_url": f"{os.environ['FRONTEND_URL']}/training/{code}"}


@api_router.get("/public/training/{code}")
async def get_public_training_session(code: str):
    session = await db.training_sessions.find_one({"code": code}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Training session not found")
    if session.get("status") == "completed":
        raise HTTPException(status_code=409, detail="Training session already completed")
    public_items = []
    for item in session.get("items", []):
        public_items.append(
            {
                "id": item["id"],
                "title": item["title"],
                "category": item["category"],
                "image_url": item["image_url"],
                "notes": item.get("notes", ""),
                "question_type": item.get("question_type", "multiple_choice"),
                "question_prompt": item.get("question_prompt", ""),
                "choice_options": item.get("choice_options", []),
            }
        )
    return {
        "session": {
            "code": session["code"],
            "crew_label": session.get("crew_label", "Crew"),
            "division": session.get("division", ""),
            "item_count": session.get("item_count", 0),
        },
        "items": public_items,
    }


@api_router.post("/public/training/{code}/submit")
async def submit_public_training_session(code: str, payload: TrainingSessionSubmitRequest):
    session = await db.training_sessions.find_one({"code": code}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Training session not found")
    if session.get("status") == "completed":
        raise HTTPException(status_code=409, detail="Training session already completed")

    answer_lookup = {answer.item_id: answer for answer in payload.answers}
    scored_answers = []
    correct_count = 0
    total_time = 0.0
    for item in session.get("items", []):
        answer = answer_lookup.get(item["id"])
        response = answer.response if answer else ""
        time_seconds = answer.time_seconds if answer else 0
        is_correct = match_training_answer(item.get("correct_answer", ""), response)
        if is_correct:
            correct_count += 1
        total_time += time_seconds
        scored_answers.append(
            {
                "item_id": item["id"],
                "response": response,
                "time_seconds": time_seconds,
                "is_correct": is_correct,
            }
        )

    item_count = max(len(session.get("items", [])), 1)
    score_percent = round(correct_count / item_count * 100, 1)
    completion_rate = round(len(payload.answers) / item_count * 100, 1)
    average_time = round(total_time / item_count, 1)
    update = {
        "status": "completed",
        "answers": scored_answers,
        "score_percent": score_percent,
        "completion_rate": completion_rate,
        "average_time_seconds": average_time,
        "completed_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.training_sessions.update_one({"code": code}, {"$set": update})
    return {
        "summary": {
            "score_percent": score_percent,
            "completion_rate": completion_rate,
            "average_time_seconds": average_time,
            "owner_message": "Great work — keep building standards that crews, clients, and reviewers can trust.",
        }
    }


@api_router.get("/submissions")
async def get_submissions(
    user: dict = Depends(require_roles("management", "owner")),
    scope: str = Query("all"),
    filter_by: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    query: dict[str, Any] = {}
    if scope == "management":
        query["status"] = {"$in": ["Pending Match", "Ready for Review", "Management Reviewed"]}
    elif scope == "owner":
        query["status"] = {"$in": ["Management Reviewed", "Owner Reviewed", "Export Ready"]}

    if filter_by == "low_confidence":
        query["match_confidence"] = {"$lt": 0.8}
    elif filter_by == "incomplete_photo_sets":
        query["$expr"] = {"$lt": ["$photo_count", "$required_photo_count"]}
    elif filter_by == "flagged":
        flagged_ids = await db.management_reviews.distinct("submission_id", {"flagged_issues": {"$ne": []}})
        query["id"] = {"$in": flagged_ids or ["__none__"]}

    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=100)
    total = await db.submissions.count_documents(query)
    submissions = (
        await db.submissions.find(query, get_submission_list_projection())
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(submissions, page, limit, total)


@api_router.get("/rapid-reviews/queue")
async def get_rapid_review_queue(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=30, max_limit=100)
    return await build_rapid_review_queue(page, limit)


@api_router.get("/submissions/{submission_id}")
async def get_submission_detail(submission_id: str, user: dict = Depends(require_roles("management", "owner"))):
    return await create_submission_snapshot(submission_id)


@api_router.post("/submissions/{submission_id}/match")
async def override_submission_match(
    submission_id: str,
    payload: MatchOverrideRequest,
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
    return snapshot


@api_router.post("/reviews/management")
async def create_management_review(
    payload: ManagementReviewRequest,
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
    return {"review": review, "submission": updated_submission}


@api_router.post("/reviews/owner")
async def create_owner_review(
    payload: OwnerReviewRequest,
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
    return {"review": review, "submission": updated_submission}


@api_router.post("/rapid-reviews")
async def create_rapid_review(
    payload: RapidReviewRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    if payload.overall_rating not in RAPID_REVIEW_RATING_MULTIPLIERS:
        raise HTTPException(status_code=400, detail="Invalid rapid review rating")
    if payload.overall_rating in {"fail", "exemplary"} and not payload.comment.strip():
        raise HTTPException(status_code=400, detail="Comments are required for fail and exemplary rapid reviews")

    snapshot = await create_submission_snapshot(payload.submission_id)
    rubric = snapshot.get("rubric")
    if not rubric:
        raise HTTPException(status_code=400, detail="Rapid review requires a matched service rubric")

    score_summary = calculate_rapid_review_score_summary(rubric, payload.overall_rating)
    review = {
        "id": make_id("rapid"),
        "submission_id": payload.submission_id,
        "reviewer_id": user["id"],
        "reviewer_role": user["role"],
        "reviewer_title": user.get("title", ""),
        "rubric_id": rubric["id"],
        "rubric_version": rubric["version"],
        "service_type": snapshot["submission"].get("service_type") or (snapshot.get("job") or {}).get("service_type", ""),
        "overall_rating": payload.overall_rating,
        "rubric_sum_percent": score_summary["rubric_sum_percent"],
        "multiplier": score_summary["multiplier"],
        "comment": payload.comment.strip(),
        "issue_tag": payload.issue_tag.strip(),
        "annotation_count": max(payload.annotation_count, 0),
        "entry_mode": payload.entry_mode,
        "swipe_duration_ms": max(payload.swipe_duration_ms, 0),
        "flagged_fast": payload.swipe_duration_ms < 4000 and payload.overall_rating in {"standard", "exemplary"},
        "flagged_concern": payload.overall_rating == "concern",
        "needs_manual_rescore": payload.overall_rating == "concern",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("rapid_reviewed", user["id"], f"Rapid review marked {payload.overall_rating}")],
    }
    await db.rapid_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await db.submissions.update_one(
        {"id": payload.submission_id},
        {
            "$set": {"updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("rapid_reviewed", user["id"], f"Rapid review marked {payload.overall_rating}")},
        },
    )
    if payload.session_id:
        swipe_log = {
            "submission_id": payload.submission_id,
            "rating": payload.overall_rating,
            "duration_ms": max(payload.swipe_duration_ms, 0),
            "flagged_fast": review["flagged_fast"],
            "timestamp": now_iso(),
        }
        await db.rapid_review_sessions.update_one(
            {"id": payload.session_id},
            {
                "$push": {"per_image_logs": swipe_log},
                "$inc": {"images_reviewed": 1, "speed_violations": 1 if review["flagged_fast"] else 0},
                "$set": {"updated_at": now_iso()},
            },
        )
    return {"rapid_review": review}


@api_router.post("/rapid-review-sessions", status_code=201)
async def start_rapid_review_session(
    payload: RapidReviewSessionStart,
    user: dict = Depends(require_roles("management", "owner")),
):
    session = {
        "id": make_id("rrs"),
        "reviewer_id": user["id"],
        "reviewer_name": user.get("name", user.get("email", "")),
        "reviewer_title": user.get("title", ""),
        "started_at": now_iso(),
        "ended_at": None,
        "total_queue_size": payload.total_queue_size,
        "images_reviewed": 0,
        "speed_violations": 0,
        "per_image_logs": [],
        "session_status": "active",
        "entry_mode": payload.entry_mode,
        "exit_reason": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.rapid_review_sessions.insert_one({**session})
    return {"session": session}


@api_router.post("/rapid-review-sessions/{session_id}/complete")
async def end_rapid_review_session(
    session_id: str,
    payload: RapidReviewSessionEnd,
    user: dict = Depends(require_roles("management", "owner")),
):
    session = await db.rapid_review_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    logs = session.get("per_image_logs", [])
    durations = [log["duration_ms"] for log in logs if log.get("duration_ms", 0) > 0]
    avg_ms = round(sum(durations) / len(durations)) if durations else 0
    speed_violations = session.get("speed_violations", 0)
    images_reviewed = session.get("images_reviewed", 0)
    violation_ratio = speed_violations / images_reviewed if images_reviewed > 0 else 0
    updates = {
        "ended_at": now_iso(),
        "session_status": "completed" if payload.exit_reason == "completed" else "exited",
        "exit_reason": payload.exit_reason,
        "average_swipe_ms": avg_ms,
        "updated_at": now_iso(),
    }
    await db.rapid_review_sessions.update_one({"id": session_id}, {"$set": updates})
    if speed_violations >= 3 or (violation_ratio > 0.3 and images_reviewed >= 5):
        await create_notification(
            title="Rapid review speed alert",
            message=f"{session.get('reviewer_name', 'Reviewer')} ({session.get('reviewer_title', '')}) completed a rapid review session with {speed_violations} fast-graded images ({images_reviewed} total, avg {round(avg_ms / 1000, 1)}s/image). Review may lack accuracy.",
            audience="admin",
            target_titles=["Owner"],
            notification_type="speed_alert",
        )
    return {"ok": True, "session_id": session_id, "images_reviewed": images_reviewed, "average_swipe_ms": avg_ms, "speed_violations": speed_violations}


@api_router.get("/rapid-review-sessions")
async def get_rapid_review_sessions(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=20, max_limit=50)
    total = await db.rapid_review_sessions.count_documents({})
    items = await db.rapid_review_sessions.find({}, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return build_paginated_response(items, page, limit, total)


@api_router.get("/rapid-reviews/flagged")
async def get_flagged_rapid_reviews(
    user: dict = Depends(require_roles("management", "owner")),
    flag_type: str = Query("concern"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=20, max_limit=50)
    query: dict[str, Any] = {}
    if flag_type == "concern":
        query["needs_manual_rescore"] = True
    elif flag_type == "fast":
        query["flagged_fast"] = True
    else:
        query["$or"] = [{"needs_manual_rescore": True}, {"flagged_fast": True}]
    total = await db.rapid_reviews.count_documents(query)
    items = await db.rapid_reviews.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return build_paginated_response(items, page, limit, total)


@api_router.patch("/rapid-reviews/{review_id}/rescore")
async def rescore_rapid_review(
    review_id: str,
    payload: RapidReviewRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    existing = await db.rapid_reviews.find_one({"id": review_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rapid review not found")
    snapshot = await create_submission_snapshot(existing["submission_id"])
    rubric = snapshot.get("rubric")
    if not rubric:
        raise HTTPException(status_code=400, detail="Rubric not found for rescore")
    score_summary = calculate_rapid_review_score_summary(rubric, payload.overall_rating)
    updates = {
        "overall_rating": payload.overall_rating,
        "rubric_sum_percent": score_summary["rubric_sum_percent"],
        "multiplier": score_summary["multiplier"],
        "comment": payload.comment.strip() if payload.comment else existing.get("comment", ""),
        "needs_manual_rescore": False,
        "rescored_by": user["id"],
        "rescored_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.rapid_reviews.update_one(
        {"id": review_id},
        {"$set": updates, "$push": {"audit_history": audit_entry("rescored", user["id"], f"Rescored from {existing['overall_rating']} to {payload.overall_rating}")}},
    )
    updated = await db.rapid_reviews.find_one({"id": review_id}, {"_id": 0})
    return serialize(updated)


@api_router.get("/analytics/summary")
async def get_analytics_summary(
    user: dict = Depends(require_roles("management", "owner")),
    period: str = Query("monthly"),
):
    period = period if period in ANALYTICS_PERIODS else "monthly"
    cutoff = get_period_cutoff(period).isoformat()
    submissions = await db.submissions.find({"created_at": {"$gte": cutoff}}, {"_id": 0}).to_list(2000)
    submission_ids = [item["id"] for item in submissions]
    review_query = {"submission_id": {"$in": submission_ids or ["__none__"]}}
    management_reviews = await db.management_reviews.find(review_query, {"_id": 0}).to_list(2000)
    owner_reviews = await db.owner_reviews.find(review_query, {"_id": 0}).to_list(2000)

    crew_scores: dict[str, list[float]] = {}
    variance_points = []
    fail_reasons: dict[str, int] = {}
    volume_by_bucket: dict[datetime, dict[str, Any]] = {}

    for submission in submissions:
        captured_at = parse_iso_datetime(submission.get("created_at"))
        if not captured_at:
            continue
        bucket_start, bucket_label = get_period_bucket(captured_at, period)
        bucket_entry = volume_by_bucket.setdefault(bucket_start, {"label": bucket_label, "count": 0})
        bucket_entry["count"] += 1

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
    fail_reason_rows = [{"reason": key, "count": value} for key, value in fail_reasons.items()]
    fail_reason_rows.sort(key=lambda item: item["count"], reverse=True)

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
    calibration_heatmap.sort(key=lambda item: (item["crew"], item["service_type"]))

    return {
        "period": period,
        "period_label": ANALYTICS_PERIODS[period]["label"],
        "average_score_by_crew": average_by_crew,
        "score_variance_average": variance_avg,
        "fail_reason_frequency": fail_reason_rows,
        "submission_volume_trends": [
            {"day": entry["label"], "count": entry["count"]}
            for _, entry in sorted(volume_by_bucket.items(), key=lambda item: item[0])
        ],
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
async def get_exports(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await db.export_records.count_documents({})
    items = (
        await db.export_records.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@api_router.get("/exports/{export_id}/download")
async def download_export(export_id: str, user: dict = Depends(require_roles("management", "owner"))):
    export_record = await db.export_records.find_one({"id": export_id}, {"_id": 0})
    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(export_record["file_path"], filename=Path(export_record["file_path"]).name)


@api_router.get("/integrations/storage/status")
async def storage_status(user: dict = Depends(require_roles("management", "owner"))):
    return get_storage_status_payload()


@api_router.get("/integrations/drive/status")
async def drive_status(user: dict = Depends(require_roles("management", "owner"))):
    storage = get_storage_status_payload()
    return {
        **storage,
        "scope": [storage["bucket"]],
    }


@api_router.get("/integrations/drive/connect")
async def connect_drive(user: dict = Depends(require_roles("management", "owner"))):
    raise HTTPException(status_code=410, detail="Google Drive sync has been retired. Supabase Storage is active.")


@api_router.get("/oauth/drive/callback")
async def drive_callback(code: str, state: str):
    raise HTTPException(status_code=410, detail="Google Drive callback is no longer used. Supabase Storage is active.")


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
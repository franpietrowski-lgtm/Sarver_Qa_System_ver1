"""
Shared dependencies used by all route modules.
Provides: db connection, auth dependencies, utility functions, storage helpers, business logic.
"""
import asyncio
import html
import json
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from auth_utils import create_access_token, decode_access_token, get_password_hash, verify_password

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = Path("/app/data")
SUBMISSIONS_DIR = DATA_DIR / "submissions"
EXPORTS_DIR = DATA_DIR / "exports"

db = None  # Initialized by server.py at startup
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


# ── Utility Functions ──────────────────────────────────────────────────

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
    return {"timestamp": now_iso(), "action": action, "actor_id": actor_id, "note": note}


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
            "page": page, "limit": limit, "total": total, "pages": total_pages,
            "has_next": page < total_pages, "has_prev": page > 1,
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
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def write_json_artifact(folder_path: str | None, filename: str, payload: dict) -> None:
    if not folder_path:
        return
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(dump_json_bytes(payload))


# ── Storage Functions ──────────────────────────────────────────────────

def storage_is_configured() -> bool:
    return all(os.environ.get(key) for key in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "STORAGE_BUCKET_SUBMISSIONS"])


def get_storage_bucket() -> str:
    return os.environ["STORAGE_BUCKET_SUBMISSIONS"]


def get_storage_status_payload() -> dict:
    configured = storage_is_configured()
    return {
        "provider": "supabase", "label": "Supabase Storage", "configured": configured, "connected": configured,
        "bucket": os.environ.get("STORAGE_BUCKET_SUBMISSIONS"), "project_url": os.environ.get("SUPABASE_URL"),
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
        get_supabase_client().storage.from_(bucket_name).upload(path, content, {"content-type": content_type, "upsert": "true"})
    await asyncio.get_event_loop().run_in_executor(None, _upload)


async def download_bytes_from_storage(path: str, bucket: str | None = None) -> bytes:
    bucket_name = bucket or get_storage_bucket()
    def _download() -> bytes:
        return get_supabase_client().storage.from_(bucket_name).download(path)
    return await asyncio.get_event_loop().run_in_executor(None, _download)


# ── URL Builders ───────────────────────────────────────────────────────

def build_storage_path(submission_id: str, folder: str, filename: str) -> str:
    return f"sarver-landscape/submissions/{submission_id}/{folder}/{filename}"


def build_submission_file_response_url(submission_id: str, filename: str) -> tuple[str, str]:
    relative_api_path = f"/api/submissions/files/{submission_id}/{filename}"
    return relative_api_path, f"{os.environ.get('FRONTEND_URL', '')}{relative_api_path}"


def build_equipment_file_response_url(log_id: str, filename: str) -> tuple[str, str]:
    relative_api_path = f"/api/equipment-logs/files/{log_id}/{filename}"
    return relative_api_path, f"{os.environ.get('FRONTEND_URL', '')}{relative_api_path}"


def build_missing_image_placeholder(filename: str) -> bytes:
    safe_name = html.escape(filename)
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='800' viewBox='0 0 1200 800'>
      <rect width='1200' height='800' fill='#edf0e7'/><rect x='70' y='70' width='1060' height='660' rx='36' fill='#d8e4da' stroke='#b8c5ba' stroke-width='4'/>
      <text x='600' y='350' text-anchor='middle' font-size='42' fill='#243e36' font-family='Arial, sans-serif'>Image temporarily unavailable</text>
      <text x='600' y='410' text-anchor='middle' font-size='24' fill='#5c6d64' font-family='Arial, sans-serif'>{safe_name}</text></svg>""".strip()
    return svg.encode("utf-8")


# ── Submission Media Helpers ───────────────────────────────────────────

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
        field_report["photo_files"] = [hydrate_file_entry(item) for item in submission.get("field_report", {}).get("photo_files", [])]
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


# ── Projections ────────────────────────────────────────────────────────

def get_submission_list_projection() -> dict:
    return {
        "_id": 0, "id": 1, "submission_code": 1, "job_id": 1, "job_name_input": 1,
        "crew_label": 1, "truck_number": 1, "division": 1, "service_type": 1,
        "task_type": 1, "status": 1, "match_status": 1, "match_confidence": 1,
        "work_date": 1, "captured_at": 1, "created_at": 1,
    }


def get_jobs_projection() -> dict:
    return {
        "_id": 0, "id": 1, "job_id": 1, "job_name": 1, "property_name": 1, "address": 1,
        "service_type": 1, "scheduled_date": 1, "division": 1, "truck_number": 1, "route": 1,
    }


def get_crew_link_projection() -> dict:
    return {
        "_id": 0, "id": 1, "code": 1, "crew_member_id": 1, "label": 1, "truck_number": 1,
        "division": 1, "assignment": 1, "enabled": 1, "archived": 1, "archived_at": 1,
        "created_at": 1, "updated_at": 1,
    }


def present_crew_link(crew_link: dict) -> dict:
    return {**crew_link, "crew_member_id": crew_link.get("crew_member_id") or crew_link.get("code", "").upper()}


# ── Auth Dependencies ──────────────────────────────────────────────────

async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
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


# ── Business Logic Helpers ─────────────────────────────────────────────

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
        "submission": hydrate_submission_media(submission), "management_review": management_review,
        "owner_review": owner_review, "rapid_review": rapid_review, "job": job, "rubric": rubric,
    }


def calculate_rapid_review_score_summary(rubric: dict, overall_rating: str) -> dict:
    total_weighted_points = sum(category["weight"] for category in rubric.get("categories", []))
    normalized_percent = round(total_weighted_points * RAPID_REVIEW_RATING_MULTIPLIERS[overall_rating] * 100, 1)
    return {
        "overall_rating": overall_rating, "rubric_sum_percent": normalized_percent,
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
        .sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


def match_training_answer(correct_answer: str, response: str) -> bool:
    accepted_values = [item.strip().lower() for item in correct_answer.split("|") if item.strip()]
    normalized_response = response.strip().lower()
    return normalized_response in accepted_values if accepted_values else False


def calculate_repeat_offender_level(count: int, thresholds: tuple[int, int, int]) -> str:
    level_one, level_two, level_three = thresholds
    if count >= level_three:
        return "Critical"
    if count >= level_two:
        return "Warning"
    if count >= level_one:
        return "Watch"
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
        crew_entry = by_crew.setdefault(crew_key, {
            "crew": crew_key, "access_code": submission.get("access_code", ""),
            "division": submission.get("division", ""), "incident_count": 0,
            "issue_types": {}, "submission_ids": [], "related_submissions": [],
        })
        crew_entry["incident_count"] += 1
        crew_entry["issue_types"][issue_type] = crew_entry["issue_types"].get(issue_type, 0) + 1
        if submission_id not in crew_entry["submission_ids"]:
            crew_entry["submission_ids"].append(submission_id)
            crew_entry["related_submissions"].append({
                "submission_id": submission_id,
                "label": submission.get("job_name_input") or submission.get("job_id") or submission_id,
                "created_at": submission.get("created_at"), "source": source,
            })
        cell_key = (crew_key, issue_type)
        cell = heatmap.setdefault(cell_key, {"crew": crew_key, "issue_type": issue_type, "count": 0, "submission_ids": []})
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
        {"created_at": {"$gte": cutoff}}, {"_id": 0, "submission_id": 1, "flagged_issues": 1, "disposition": 1},
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
        "window_days": days, "thresholds": {"level_1": thresholds[0], "level_2": thresholds[1], "level_3": thresholds[2]},
        "crew_summaries": crew_summaries, "heatmap": heatmap_rows,
    }


async def get_recent_training_sessions(page: int, limit: int) -> dict:
    total = await db.training_sessions.count_documents({})
    items = (
        await db.training_sessions.find({}, {"_id": 0}).sort("created_at", -1)
        .skip((page - 1) * limit).limit(limit).to_list(limit)
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
    title: str, message: str, audience: str,
    related_submission_id: str | None = None, target_role: str | None = None,
    target_titles: list[str] | None = None, target_access_code: str | None = None,
    target_user_id: str | None = None, related_job_id: str | None = None,
    notification_type: str = "info",
) -> dict:
    notification = {
        "id": make_id("note"), "title": title, "message": message, "audience": audience,
        "target_role": target_role, "target_titles": target_titles or [],
        "target_access_code": target_access_code, "target_user_id": target_user_id,
        "related_submission_id": related_submission_id, "related_job_id": related_job_id,
        "notification_type": notification_type, "status": "unread",
        "created_at": now_iso(), "updated_at": now_iso(),
        "audit_history": [audit_entry("created", "system", title)],
    }
    await db.notifications.insert_one({**notification})
    return notification

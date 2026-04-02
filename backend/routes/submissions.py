import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

import shared.deps as deps
from shared.deps import (
    require_roles, now_iso, audit_entry,
    normalize_page, normalize_limit, build_paginated_response,
    get_submission_list_projection,
    download_bytes_from_storage, get_storage_bucket,
    build_missing_image_placeholder, find_submission_file_entry,
    create_submission_snapshot, write_json_artifact,
)
from shared.models import MatchOverrideRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/submissions/files/{submission_id}/{filename}")
async def get_submission_file(submission_id: str, filename: str):
    submission = await deps.db.submissions.find_one(
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


@router.get("/submissions")
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
        flagged_ids = await deps.db.management_reviews.distinct("submission_id", {"flagged_issues": {"$ne": []}})
        query["id"] = {"$in": flagged_ids or ["__none__"]}

    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=100)
    total = await deps.db.submissions.count_documents(query)
    submissions = (
        await deps.db.submissions.find(query, get_submission_list_projection())
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(submissions, page, limit, total)


@router.get("/submissions/{submission_id}")
async def get_submission_detail(submission_id: str, user: dict = Depends(require_roles("management", "owner"))):
    return await create_submission_snapshot(submission_id)


@router.post("/submissions/{submission_id}/match")
async def override_submission_match(
    submission_id: str,
    payload: MatchOverrideRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    submission = await deps.db.submissions.find_one({"id": submission_id}, {"_id": 0})
    job = await deps.db.jobs.find_one({"id": payload.job_id}, {"_id": 0})
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
    await deps.db.submissions.update_one(
        {"id": submission_id},
        {
            "$set": update,
            "$push": {"audit_history": audit_entry("match_override", user["id"], f"Matched to {job['job_id']}")},
        },
    )
    snapshot = await create_submission_snapshot(submission_id)
    write_json_artifact(snapshot["submission"].get("local_folder_path"), "metadata.json", snapshot["submission"])
    return snapshot

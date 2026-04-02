import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

import shared.deps as deps
from shared.deps import (
    require_roles, now_iso, audit_entry,
    normalize_page, normalize_limit, build_paginated_response,
    download_bytes_from_storage, get_storage_bucket,
    build_missing_image_placeholder, create_notification,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/equipment-logs")
async def get_equipment_logs(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await deps.db.equipment_logs.count_documents({})
    items = (
        await deps.db.equipment_logs.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@router.post("/equipment-logs/{log_id}/forward-to-owner")
async def forward_equipment_log_to_owner(log_id: str, user: dict = Depends(require_roles("management", "owner"))):
    if user.get("title") != "GM" and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only GM or Owner can forward this red-tag to Owner review")
    equipment_log = await deps.db.equipment_logs.find_one({"id": log_id}, {"_id": 0})
    if not equipment_log:
        raise HTTPException(status_code=404, detail="Equipment log not found")
    await deps.db.equipment_logs.update_one(
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


@router.get("/equipment-logs/files/{log_id}/{filename}")
async def get_equipment_log_file(log_id: str, filename: str):
    equipment_log = await deps.db.equipment_logs.find_one({"id": log_id}, {"_id": 0, "photos": 1})
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

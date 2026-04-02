import csv
import io
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry,
    normalize_key, normalize_page, normalize_limit,
    build_paginated_response, get_jobs_projection,
)

router = APIRouter()


@router.get("/jobs")
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
    total = await deps.db.jobs.count_documents(query)
    jobs = (
        await deps.db.jobs.find(query, get_jobs_projection())
        .sort("scheduled_date", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(jobs, page, limit, total)


@router.post("/jobs/import-csv")
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
        existing = await deps.db.jobs.find_one({"job_id": job_payload["job_id"]}, {"_id": 0})
        if existing:
            await deps.db.jobs.update_one(
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
        await deps.db.jobs.insert_many(normalized_rows)

    return {"imported": imported, "updated": updated, "filename": file.filename}

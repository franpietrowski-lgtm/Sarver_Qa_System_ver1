import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry,
    normalize_page, normalize_limit, build_paginated_response,
    EXPORTS_DIR,
)
from shared.models import ExportRunRequest

router = APIRouter()


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


@router.post("/exports/run")
async def run_export(payload: ExportRunRequest, user: dict = Depends(require_roles("management", "owner"))):
    submissions = await deps.db.submissions.find({}, {"_id": 0}).to_list(5000)
    management_reviews = await deps.db.management_reviews.find({}, {"_id": 0}).to_list(5000)
    owner_reviews = await deps.db.owner_reviews.find({}, {"_id": 0}).to_list(5000)
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
    await deps.db.export_records.insert_one({**record})
    await deps.db.submissions.update_many(
        {"id": {"$in": [row["submission_id"] for row in rows]}},
        {
            "$set": {"last_exported_at": now_iso(), "last_export_id": export_id, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("dataset_exported", user["id"], export_id)},
        },
    )
    return record


@router.get("/exports")
async def get_exports(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await deps.db.export_records.count_documents({})
    items = (
        await deps.db.export_records.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@router.get("/exports/{export_id}/download")
async def download_export(export_id: str, user: dict = Depends(require_roles("management", "owner"))):
    export_record = await deps.db.export_records.find_one({"id": export_id}, {"_id": 0})
    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(export_record["file_path"], filename=Path(export_record["file_path"]).name)

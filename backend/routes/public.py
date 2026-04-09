import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

import shared.deps as deps
from shared.deps import (
    make_id, now_iso, audit_entry,
    build_submission_file_response_url, build_equipment_file_response_url,
    build_storage_path, upload_bytes_to_storage, get_storage_bucket,
    hydrate_submission_media, compute_match, get_active_rubric,
    present_crew_link, create_notification, write_json_artifact,
    utc_now, match_training_answer, select_training_snapshots,
    SUBMISSIONS_DIR,
)
from shared.models import TrainingSessionSubmitRequest

router = APIRouter()


@router.get("/public/crew-access")
async def get_public_crew_access():
    crew_links = await deps.db.crew_access_links.find({"enabled": True}, {"_id": 0}).to_list(100)
    return [present_crew_link(link) for link in crew_links]


@router.get("/public/crew-access/{code}")
async def get_crew_access_link(code: str):
    crew_link = await deps.db.crew_access_links.find_one({"code": code, "enabled": True}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    notifications = await deps.db.notifications.find(
        {"audience": "crew", "target_access_code": code, "status": "unread"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(20)
    return {**present_crew_link(crew_link), "notifications": notifications}



@router.get("/public/standards")
async def get_public_standards(division: str = "all"):
    query = {"is_active": {"$ne": False}}
    if division != "all":
        query["$or"] = [{"division_targets": []}, {"division_targets": division}]
    items = await deps.db.standards_library.find(query, {"_id": 0}).sort("category", 1).to_list(200)
    return {"standards": items}



@router.get("/public/jobs")
async def get_public_jobs(search: str = "", access_code: str | None = None):
    query: dict[str, Any] = {}
    crew_link = None
    if access_code:
        crew_link = await deps.db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
        if crew_link:
            query["truck_number"] = crew_link["truck_number"]
    if search:
        query["search_text"] = {"$regex": search.lower()}
    jobs = await deps.db.jobs.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(100)
    return {"jobs": jobs, "crew_link": crew_link}


@router.post("/public/submissions")
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
    work_date: str = Form(""),
    issue_type: str = Form(""),
    issue_notes: str = Form(""),
    photos: list[UploadFile] = File([]),
    issue_photos: list[UploadFile] = File([]),
    member_code: str = Form(""),
):
    crew_link = await deps.db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew access link not found")
    job = await deps.db.jobs.find_one({"id": job_id}, {"_id": 0}) if job_id else None
    if not job and not job_name.strip():
        raise HTTPException(status_code=400, detail="Job name is required")

    required_photo_count = 3
    if job and job.get("service_type"):
        rubric = await get_active_rubric(job["service_type"])
        required_photo_count = rubric.get("min_photos", 3)

    # Emergency submissions (incident/damage) bypass photo requirement
    is_emergency = bool(issue_type and ("incident" in issue_type.lower() or "accident" in issue_type.lower()))
    if not is_emergency and len(photos) < required_photo_count:
        raise HTTPException(
            status_code=400,
            detail=f"At least {required_photo_count} photos are required for this submission",
        )

    recent_cutoff = (utc_now() - timedelta(minutes=15)).isoformat()
    job_key = job["job_id"] if job else job_name.strip().lower()
    duplicate = await deps.db.submissions.find_one(
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
        "gps_low_confidence": gps_accuracy > 2.0,
        "work_date": work_date or now_iso()[:10],
        "captured_at": now_iso(),
        "required_photo_count": required_photo_count,
        "photo_count": len(photo_files),
        "photo_files": photo_files,
        "local_folder_path": str(local_folder),
        "device_metadata": {"user_agent": request.headers.get("user-agent", "unknown")},
        "storage_status": "stored",
        "member_code": member_code if member_code else None,
        "is_emergency": is_emergency,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [
            audit_entry("submitted", access_code, "Crew submission created"),
            audit_entry("status_change", access_code, f"Lifecycle moved to {status}"),
        ],
    }
    write_json_artifact(str(local_folder), "metadata.json", submission)
    await deps.db.notifications.update_many(
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
    await deps.db.submissions.insert_one({**submission})
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
        # Determine if this is a true emergency (incident/accident)
        notification_type_val = "emergency_incident" if is_emergency else "field_issue"
        notification_title = (
            "EMERGENCY: Incident/Accident Report Filed"
            if is_emergency
            else "Crew reported an issue or damage"
        )
        target_roles = (
            ["Supervisor", "Production Manager", "Account Manager", "GM", "Owner"]
            if is_emergency
            else ["Supervisor", "Production Manager", "Account Manager", "GM"]
        )
        await create_notification(
            title=notification_title,
            message=f"{crew_link['label']} reported '{issue_type or 'field issue'}' on {job_name_value}.",
            audience="management" if not is_emergency else "all",
            target_titles=target_roles,
            related_submission_id=submission_id,
            related_job_id=job_key,
            notification_type=notification_type_val,
        )
    return {"submission": hydrate_submission_media(submission)}


@router.post("/public/equipment-logs")
async def create_equipment_log(
    request: Request,
    access_code: str = Form(...),
    equipment_number: str = Form(...),
    general_note: str = Form(""),
    red_tag_note: str = Form(""),
    pre_service_photo: UploadFile = File(...),
    post_service_photo: UploadFile = File(...),
):
    crew_link = await deps.db.crew_access_links.find_one({"code": access_code, "enabled": True}, {"_id": 0})
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
    await deps.db.equipment_logs.insert_one({**log})
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


@router.get("/public/training/{code}")
async def get_public_training_session(code: str):
    session = await deps.db.training_sessions.find_one({"code": code}, {"_id": 0})
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


@router.post("/public/training/{code}/submit")
async def submit_public_training_session(code: str, payload: TrainingSessionSubmitRequest):
    session = await deps.db.training_sessions.find_one({"code": code}, {"_id": 0})
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
    await deps.db.training_sessions.update_one({"code": code}, {"$set": update})
    return {
        "summary": {
            "score_percent": score_percent,
            "completion_rate": completion_rate,
            "average_time_seconds": average_time,
            "owner_message": "Great work — keep building standards that crews, clients, and reviewers can trust.",
        }
    }



@router.get("/public/crew-submissions/{access_code}")
async def get_crew_submissions(access_code: str, page: int = 1, limit: int = 20):
    """Return submission history for a crew QR access code."""
    crew_link = await deps.db.crew_access_links.find_one({"code": access_code}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    skip = (max(page, 1) - 1) * limit
    pipeline = [
        {"$match": {"access_code": access_code}},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {
            "_id": 0, "id": 1, "submission_code": 1, "job_name_input": 1, "job_id": 1,
            "service_type": 1, "division": 1, "truck_number": 1, "work_date": 1,
            "status": 1, "note": 1, "area_tag": 1, "photo_count": 1,
            "is_emergency": 1, "created_at": 1,
            "management_review_score": "$management_review.total_score",
            "management_review_verdict": "$management_review.verdict",
        }},
    ]
    docs = await deps.db.submissions.aggregate(pipeline).to_list(limit)
    total = await deps.db.submissions.count_documents({"access_code": access_code})
    return {"submissions": docs, "total": total, "page": page, "crew_label": crew_link.get("label", "")}

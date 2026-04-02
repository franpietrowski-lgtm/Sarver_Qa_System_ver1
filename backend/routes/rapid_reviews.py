from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry, serialize,
    normalize_page, normalize_limit, build_paginated_response,
    build_rapid_review_queue, create_submission_snapshot,
    calculate_rapid_review_score_summary, create_notification,
    RAPID_REVIEW_RATING_MULTIPLIERS,
)
from shared.models import (
    RapidReviewRequest, RapidReviewSessionStart, RapidReviewSessionEnd,
)

router = APIRouter()


@router.get("/rapid-reviews/queue")
async def get_rapid_review_queue(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=30, max_limit=100)
    return await build_rapid_review_queue(page, limit)


@router.post("/rapid-reviews")
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
    await deps.db.rapid_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await deps.db.submissions.update_one(
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
        await deps.db.rapid_review_sessions.update_one(
            {"id": payload.session_id},
            {
                "$push": {"per_image_logs": swipe_log},
                "$inc": {"images_reviewed": 1, "speed_violations": 1 if review["flagged_fast"] else 0},
                "$set": {"updated_at": now_iso()},
            },
        )
    return {"rapid_review": review}


@router.post("/rapid-review-sessions", status_code=201)
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
    await deps.db.rapid_review_sessions.insert_one({**session})
    return {"session": session}


@router.post("/rapid-review-sessions/{session_id}/complete")
async def end_rapid_review_session(
    session_id: str,
    payload: RapidReviewSessionEnd,
    user: dict = Depends(require_roles("management", "owner")),
):
    session = await deps.db.rapid_review_sessions.find_one({"id": session_id}, {"_id": 0})
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
    await deps.db.rapid_review_sessions.update_one({"id": session_id}, {"$set": updates})
    if speed_violations >= 3 or (violation_ratio > 0.3 and images_reviewed >= 5):
        await create_notification(
            title="Rapid review speed alert",
            message=f"{session.get('reviewer_name', 'Reviewer')} ({session.get('reviewer_title', '')}) completed a rapid review session with {speed_violations} fast-graded images ({images_reviewed} total, avg {round(avg_ms / 1000, 1)}s/image). Review may lack accuracy.",
            audience="admin",
            target_titles=["Owner"],
            notification_type="speed_alert",
        )
    return {"ok": True, "session_id": session_id, "images_reviewed": images_reviewed, "average_swipe_ms": avg_ms, "speed_violations": speed_violations}


@router.get("/rapid-review-sessions")
async def get_rapid_review_sessions(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=20, max_limit=50)
    total = await deps.db.rapid_review_sessions.count_documents({})
    items = await deps.db.rapid_review_sessions.find({}, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return build_paginated_response(items, page, limit, total)


@router.get("/rapid-reviews/flagged")
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
    total = await deps.db.rapid_reviews.count_documents(query)
    items = await deps.db.rapid_reviews.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return build_paginated_response(items, page, limit, total)


@router.patch("/rapid-reviews/{review_id}/rescore")
async def rescore_rapid_review(
    review_id: str,
    payload: RapidReviewRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    existing = await deps.db.rapid_reviews.find_one({"id": review_id}, {"_id": 0})
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
    await deps.db.rapid_reviews.update_one(
        {"id": review_id},
        {"$set": updates, "$push": {"audit_history": audit_entry("rescored", user["id"], f"Rescored from {existing['overall_rating']} to {payload.overall_rating}")}},
    )
    updated = await deps.db.rapid_reviews.find_one({"id": review_id}, {"_id": 0})
    return serialize(updated)

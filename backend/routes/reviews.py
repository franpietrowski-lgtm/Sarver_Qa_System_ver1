from fastapi import APIRouter, Depends, HTTPException

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry,
    get_active_rubric, calculate_total_score,
    create_submission_snapshot, create_notification,
    write_json_artifact,
)
from shared.models import ManagementReviewRequest, OwnerReviewRequest

router = APIRouter()


@router.post("/reviews/management")
async def create_management_review(
    payload: ManagementReviewRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    submission = await deps.db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
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
    await deps.db.management_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await deps.db.submissions.update_one(
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
    updated_submission = await deps.db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    return {"review": review, "submission": updated_submission}


@router.post("/reviews/owner")
async def create_owner_review(
    payload: OwnerReviewRequest,
    user: dict = Depends(require_roles("owner")),
):
    submission = await deps.db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    rubric = await get_active_rubric(submission["service_type"])
    total_score = calculate_total_score(rubric, payload.category_scores)
    management_review = await deps.db.management_reviews.find_one({"submission_id": payload.submission_id}, {"_id": 0})
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
    await deps.db.owner_reviews.update_one(
        {"submission_id": payload.submission_id},
        {"$set": review},
        upsert=True,
    )
    await deps.db.submissions.update_one(
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
    updated_submission = await deps.db.submissions.find_one({"id": payload.submission_id}, {"_id": 0})
    return {"review": review, "submission": updated_submission}

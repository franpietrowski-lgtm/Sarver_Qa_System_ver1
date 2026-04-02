from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

import shared.deps as deps
from shared.deps import (
    require_roles, get_storage_status_payload,
    ANALYTICS_PERIODS, get_period_cutoff, get_period_bucket,
    parse_iso_datetime,
)

router = APIRouter()


@router.get("/dashboard/overview")
async def get_dashboard_overview(user: dict = Depends(require_roles("management", "owner"))):
    submissions_count = await deps.db.submissions.count_documents({})
    jobs_count = await deps.db.jobs.count_documents({})
    rubrics_count = await deps.db.rubric_definitions.count_documents({})
    export_count = await deps.db.export_records.count_documents({})
    management_queue = await deps.db.submissions.count_documents({"status": {"$in": ["Pending Match", "Ready for Review"]}})
    owner_queue = await deps.db.submissions.count_documents({"status": {"$in": ["Management Reviewed", "Owner Reviewed"]}})
    export_ready = await deps.db.submissions.count_documents({"status": "Export Ready"})
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


@router.get("/analytics/summary")
async def get_analytics_summary(
    user: dict = Depends(require_roles("management", "owner")),
    period: str = Query("monthly"),
):
    period = period if period in ANALYTICS_PERIODS else "monthly"
    cutoff = get_period_cutoff(period).isoformat()
    submissions = await deps.db.submissions.find({"created_at": {"$gte": cutoff}}, {"_id": 0}).to_list(2000)
    submission_ids = [item["id"] for item in submissions]
    review_query = {"submission_id": {"$in": submission_ids or ["__none__"]}}
    management_reviews = await deps.db.management_reviews.find(review_query, {"_id": 0}).to_list(2000)
    owner_reviews = await deps.db.owner_reviews.find(review_query, {"_id": 0}).to_list(2000)

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

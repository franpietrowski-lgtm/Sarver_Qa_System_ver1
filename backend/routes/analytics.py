from datetime import datetime
from random import sample as random_sample
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
    submissions = await deps.db.submissions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "id": 1, "created_at": 1, "crew_label": 1, "truck_number": 1, "service_type": 1},
    ).to_list(2000)
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


@router.get("/analytics/random-sample")
async def get_random_sample(
    user: dict = Depends(require_roles("owner")),
    size: int = Query(10, ge=1, le=50),
    crew: str = Query(None),
    division: str = Query(None),
    service_type: str = Query(None),
    period: str = Query("monthly"),
):
    period = period if period in ANALYTICS_PERIODS else "monthly"
    cutoff = get_period_cutoff(period).isoformat()
    query: dict[str, Any] = {"created_at": {"$gte": cutoff}}
    if crew:
        query["crew_label"] = crew
    if division:
        query["division"] = division
    if service_type:
        query["service_type"] = service_type

    submissions = await deps.db.submissions.find(
        query,
        {"_id": 0, "id": 1, "created_at": 1, "crew_label": 1, "division": 1,
         "service_type": 1, "truck_number": 1, "status": 1, "image_urls": 1},
    ).to_list(5000)

    sampled = random_sample(submissions, min(size, len(submissions))) if submissions else []
    sampled_ids = [s["id"] for s in sampled]

    mgmt_reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sampled_ids or ["__none__"]}},
        {"_id": 0, "submission_id": 1, "total_score": 1, "overall_rating": 1,
         "flagged_issues": 1, "reviewer_id": 1},
    ).to_list(500)

    owner_reviews = await deps.db.owner_reviews.find(
        {"submission_id": {"$in": sampled_ids or ["__none__"]}},
        {"_id": 0, "submission_id": 1, "total_score": 1, "training_inclusion": 1,
         "variance_from_management": 1},
    ).to_list(500)

    mgmt_lookup = {r["submission_id"]: r for r in mgmt_reviews}
    owner_lookup = {r["submission_id"]: r for r in owner_reviews}

    results = []
    for sub in sampled:
        mgmt = mgmt_lookup.get(sub["id"])
        owner = owner_lookup.get(sub["id"])
        results.append({
            "submission_id": sub["id"],
            "crew": sub.get("crew_label") or sub.get("truck_number", ""),
            "division": sub.get("division", ""),
            "service_type": sub.get("service_type", ""),
            "status": sub.get("status", ""),
            "created_at": sub.get("created_at", ""),
            "image_count": len(sub.get("image_urls") or []),
            "management_score": mgmt["total_score"] if mgmt else None,
            "management_rating": mgmt.get("overall_rating") if mgmt else None,
            "management_issues": mgmt.get("flagged_issues", []) if mgmt else [],
            "owner_score": owner["total_score"] if owner else None,
            "owner_training": owner.get("training_inclusion") if owner else None,
            "variance": owner.get("variance_from_management") if owner else None,
        })

    # Collect filter options from the full dataset
    all_crews = await deps.db.submissions.distinct("crew_label", {"created_at": {"$gte": cutoff}})
    all_divisions = await deps.db.submissions.distinct("division", {"created_at": {"$gte": cutoff}})
    all_service_types = await deps.db.submissions.distinct("service_type", {"created_at": {"$gte": cutoff}})

    return {
        "pool_size": len(submissions),
        "sample_size": len(results),
        "samples": results,
        "filter_options": {
            "crews": sorted([c for c in all_crews if c]),
            "divisions": sorted([d for d in all_divisions if d]),
            "service_types": sorted([s for s in all_service_types if s]),
        },
    }


@router.get("/analytics/variance-drilldown")
async def get_variance_drilldown(
    user: dict = Depends(require_roles("owner")),
    crew: str = Query(...),
    service_type: str = Query(...),
    period: str = Query("monthly"),
):
    period = period if period in ANALYTICS_PERIODS else "monthly"
    cutoff = get_period_cutoff(period).isoformat()
    submissions = await deps.db.submissions.find(
        {"created_at": {"$gte": cutoff}, "crew_label": crew, "service_type": service_type},
        {"_id": 0, "id": 1, "created_at": 1, "crew_label": 1, "service_type": 1,
         "truck_number": 1, "status": 1},
    ).to_list(1000)

    sub_ids = [s["id"] for s in submissions]
    mgmt_reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}},
        {"_id": 0, "submission_id": 1, "total_score": 1, "overall_rating": 1,
         "flagged_issues": 1, "reviewer_id": 1},
    ).to_list(1000)

    owner_reviews = await deps.db.owner_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}},
        {"_id": 0, "submission_id": 1, "total_score": 1, "training_inclusion": 1,
         "variance_from_management": 1, "exclusion_reason": 1},
    ).to_list(1000)

    mgmt_lookup = {r["submission_id"]: r for r in mgmt_reviews}
    owner_lookup = {r["submission_id"]: r for r in owner_reviews}

    rows = []
    for sub in submissions:
        mgmt = mgmt_lookup.get(sub["id"])
        owner = owner_lookup.get(sub["id"])
        if not mgmt and not owner:
            continue
        rows.append({
            "submission_id": sub["id"],
            "created_at": sub.get("created_at", ""),
            "status": sub.get("status", ""),
            "management_score": mgmt["total_score"] if mgmt else None,
            "management_rating": mgmt.get("overall_rating") if mgmt else None,
            "management_issues": mgmt.get("flagged_issues", []) if mgmt else [],
            "owner_score": owner["total_score"] if owner else None,
            "owner_training": owner.get("training_inclusion") if owner else None,
            "variance": owner.get("variance_from_management") if owner else None,
            "exclusion_reason": owner.get("exclusion_reason") if owner else None,
        })

    rows.sort(key=lambda r: abs(r["variance"] or 0), reverse=True)

    return {
        "crew": crew,
        "service_type": service_type,
        "period": period,
        "total_reviewed": len(rows),
        "rows": rows,
    }



# ─── ROLE-SPECIFIC METRIC ENDPOINTS ───

@router.get("/metrics/division-quality-trend")
async def division_quality_trend(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = Query("all"),
):
    """Rolling 30/60/90 day average scores per division."""
    from datetime import timedelta, timezone
    now = datetime.now(timezone.utc)
    results = {}
    for days_label, days in [("30d", 30), ("60d", 60), ("90d", 90)]:
        cutoff = (now - timedelta(days=days)).isoformat()
        query = {"created_at": {"$gte": cutoff}}
        if division != "all":
            query["division"] = division
        subs = await deps.db.submissions.find(query, {"_id": 0, "id": 1, "access_code": 1, "division": 1}).to_list(2000)
        sub_ids = [s["id"] for s in subs]
        reviews = await deps.db.management_reviews.find(
            {"submission_id": {"$in": sub_ids or ["__none__"]}},
            {"_id": 0, "overall_score": 1, "submission_id": 1}
        ).to_list(2000)
        div_scores = {}
        sub_div = {s["id"]: s.get("division", "Unknown") for s in subs}
        for r in reviews:
            d = sub_div.get(r.get("submission_id"), "Unknown")
            div_scores.setdefault(d, []).append(r.get("overall_score", 0))
        results[days_label] = {
            d: round(sum(scores) / max(len(scores), 1), 2)
            for d, scores in div_scores.items()
        }
    return {"trends": results}


@router.get("/metrics/standards-compliance")
async def standards_compliance(
    user: dict = Depends(require_roles("management", "owner")),
):
    """% of submissions passing vs failing per standard check."""
    training = await deps.db.training_sessions.find(
        {}, {"_id": 0, "standard_title": 1, "status": 1, "score_percent": 1}
    ).to_list(1000)
    standards_map = {}
    for t in training:
        title = t.get("standard_title", "Unknown")
        entry = standards_map.setdefault(title, {"total": 0, "passed": 0, "avg_score": []})
        entry["total"] += 1
        if t.get("status") == "completed":
            entry["passed"] += 1
        if t.get("score_percent"):
            entry["avg_score"].append(t["score_percent"])
    rows = []
    for title, data in sorted(standards_map.items()):
        rows.append({
            "standard": title,
            "total": data["total"],
            "passed": data["passed"],
            "compliance_pct": round(data["passed"] / max(data["total"], 1) * 100, 1),
            "avg_score": round(sum(data["avg_score"]) / max(len(data["avg_score"]), 1), 1) if data["avg_score"] else 0,
        })
    rows.sort(key=lambda x: x["compliance_pct"])
    return {"standards": rows}


@router.get("/metrics/training-funnel")
async def training_funnel(
    user: dict = Depends(require_roles("management", "owner")),
):
    """Training completion funnel: total crews → viewed standards → attempted quiz → passed."""
    total_crews = await deps.db.crew_access_links.count_documents({"enabled": True})
    total_members = await deps.db.crew_members.count_documents({"active": True})
    all_training = await deps.db.training_sessions.find(
        {}, {"_id": 0, "access_code": 1, "member_code": 1, "status": 1}
    ).to_list(1000)
    codes_attempted = set()
    codes_passed = set()
    for t in all_training:
        key = t.get("member_code") or t.get("access_code", "")
        codes_attempted.add(key)
        if t.get("status") == "completed":
            codes_passed.add(key)
    return {
        "total_people": total_crews + total_members,
        "total_crews": total_crews,
        "total_members": total_members,
        "attempted_training": len(codes_attempted),
        "passed_training": len(codes_passed),
        "funnel_pct": {
            "attempted": round(len(codes_attempted) / max(total_crews + total_members, 1) * 100, 1),
            "passed": round(len(codes_passed) / max(total_crews + total_members, 1) * 100, 1),
        },
    }


@router.get("/metrics/pm-dashboard")
async def pm_dashboard_metrics(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = Query(...),
):
    """PM-scoped metrics: submission count, avg score, training completion for their division."""
    from datetime import timedelta, timezone
    now = datetime.now(timezone.utc)
    cutoff_30 = (now - timedelta(days=30)).isoformat()
    cutoff_90 = (now - timedelta(days=90)).isoformat()

    sub_30 = await deps.db.submissions.count_documents({"division": division, "created_at": {"$gte": cutoff_30}})
    sub_90 = await deps.db.submissions.count_documents({"division": division, "created_at": {"$gte": cutoff_90}})
    subs_90 = await deps.db.submissions.find(
        {"division": division, "created_at": {"$gte": cutoff_90}},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    sub_ids = [s["id"] for s in subs_90]
    reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}},
        {"_id": 0, "overall_score": 1, "verdict": 1}
    ).to_list(1000)
    scores = [r.get("overall_score", 0) for r in reviews if r.get("overall_score")]
    avg_score = round(sum(scores) / max(len(scores), 1), 2) if scores else 0
    pass_count = sum(1 for r in reviews if r.get("verdict") in ("Pass", "Exemplary"))
    fail_count = sum(1 for r in reviews if r.get("verdict") == "Fail")

    crews = await deps.db.crew_access_links.find(
        {"division": division, "enabled": True}, {"_id": 0, "code": 1, "label": 1, "leader_name": 1}
    ).to_list(20)
    crew_codes = [c["code"] for c in crews]
    training = await deps.db.training_sessions.find(
        {"access_code": {"$in": crew_codes}}, {"_id": 0, "status": 1}
    ).to_list(500)
    training_completed = sum(1 for t in training if t.get("status") == "completed")

    return {
        "division": division,
        "submissions_30d": sub_30,
        "submissions_90d": sub_90,
        "avg_score_90d": avg_score,
        "reviews_total": len(reviews),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "crews": len(crews),
        "training_total": len(training),
        "training_completed": training_completed,
    }

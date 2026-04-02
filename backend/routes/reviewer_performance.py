from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

import shared.deps as deps
from shared.deps import (
    require_roles, utc_now, parse_iso_datetime,
)

router = APIRouter()


@router.get("/analytics/reviewer-performance")
async def get_reviewer_performance(
    user: dict = Depends(require_roles("owner")),
    days: int = Query(90, ge=7, le=365),
):
    cutoff = (utc_now() - timedelta(days=days)).isoformat()

    # Fetch all rapid reviews and sessions in the window
    rapid_reviews = await deps.db.rapid_reviews.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "reviewer_id": 1, "reviewer_role": 1, "reviewer_title": 1,
         "overall_rating": 1, "swipe_duration_ms": 1, "flagged_fast": 1,
         "rubric_sum_percent": 1, "submission_id": 1, "created_at": 1},
    ).to_list(10000)

    sessions = await deps.db.rapid_review_sessions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "reviewer_id": 1, "reviewer_name": 1, "reviewer_title": 1,
         "images_reviewed": 1, "speed_violations": 1, "average_swipe_ms": 1,
         "session_status": 1, "started_at": 1, "ended_at": 1, "created_at": 1,
         "per_image_logs": 1},
    ).to_list(5000)

    # Fetch owner reviews for calibration drift
    owner_reviews_lookup: dict[str, float] = {}
    reviewed_sids = list({r["submission_id"] for r in rapid_reviews})
    if reviewed_sids:
        owner_reviews = await deps.db.owner_reviews.find(
            {"submission_id": {"$in": reviewed_sids}},
            {"_id": 0, "submission_id": 1, "total_score": 1},
        ).to_list(10000)
        owner_reviews_lookup = {r["submission_id"]: r["total_score"] for r in owner_reviews}

    # Fetch user names
    reviewer_ids = list({r["reviewer_id"] for r in rapid_reviews} | {s["reviewer_id"] for s in sessions})
    users = await deps.db.users.find(
        {"id": {"$in": reviewer_ids}},
        {"_id": 0, "id": 1, "name": 1, "title": 1, "email": 1},
    ).to_list(200)
    user_lookup = {u["id"]: u for u in users}

    # Aggregate per reviewer
    reviewer_data: dict[str, dict[str, Any]] = {}

    for review in rapid_reviews:
        rid = review["reviewer_id"]
        entry = reviewer_data.setdefault(rid, {
            "reviewer_id": rid,
            "reviewer_name": "",
            "reviewer_title": review.get("reviewer_title", ""),
            "total_reviews": 0,
            "rating_distribution": {"fail": 0, "concern": 0, "standard": 0, "exemplary": 0},
            "flagged_fast_count": 0,
            "durations_ms": [],
            "scores": [],
            "calibration_pairs": [],
            "weekly_speed": {},
        })
        entry["total_reviews"] += 1
        rating = review.get("overall_rating", "standard")
        if rating in entry["rating_distribution"]:
            entry["rating_distribution"][rating] += 1
        if review.get("flagged_fast"):
            entry["flagged_fast_count"] += 1
        dur = review.get("swipe_duration_ms", 0)
        if dur > 0:
            entry["durations_ms"].append(dur)
        if review.get("rubric_sum_percent") is not None:
            entry["scores"].append(review["rubric_sum_percent"])

        # Calibration: compare reviewer score vs owner score for same submission
        sid = review["submission_id"]
        if sid in owner_reviews_lookup:
            entry["calibration_pairs"].append({
                "reviewer_score": review.get("rubric_sum_percent", 0),
                "owner_score": owner_reviews_lookup[sid],
            })

        # Weekly speed buckets
        created = parse_iso_datetime(review.get("created_at"))
        if created and dur > 0:
            week_key = created.strftime("%Y-W%U")
            bucket = entry["weekly_speed"].setdefault(week_key, {"durations": [], "label": week_key})
            bucket["durations"].append(dur)

    # Enrich with session counts
    session_counts: dict[str, int] = {}
    for s in sessions:
        rid = s["reviewer_id"]
        session_counts[rid] = session_counts.get(rid, 0) + 1
        entry = reviewer_data.get(rid)
        if entry and not entry["reviewer_name"]:
            entry["reviewer_name"] = s.get("reviewer_name", "")

    # Build response
    reviewers = []
    for rid, data in reviewer_data.items():
        u = user_lookup.get(rid, {})
        name = u.get("name") or data.get("reviewer_name") or u.get("email", rid)
        title = u.get("title") or data.get("reviewer_title", "")
        durations = data["durations_ms"]
        avg_ms = round(sum(durations) / len(durations)) if durations else 0
        scores = data["scores"]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        # Calibration drift
        pairs = data["calibration_pairs"]
        if pairs:
            drifts = [abs(p["reviewer_score"] - p["owner_score"]) for p in pairs]
            avg_drift = round(sum(drifts) / len(drifts), 1)
            drift_direction = round(
                sum(p["reviewer_score"] - p["owner_score"] for p in pairs) / len(pairs), 1
            )
        else:
            avg_drift = 0
            drift_direction = 0

        # Speed trend (weekly averages)
        speed_trend = []
        for week_key in sorted(data["weekly_speed"].keys()):
            bucket = data["weekly_speed"][week_key]
            d = bucket["durations"]
            speed_trend.append({
                "week": bucket["label"],
                "avg_ms": round(sum(d) / len(d)),
                "count": len(d),
            })

        flagged_pct = round(data["flagged_fast_count"] / max(data["total_reviews"], 1) * 100, 1)

        reviewers.append({
            "reviewer_id": rid,
            "name": name,
            "title": title,
            "session_count": session_counts.get(rid, 0),
            "total_reviews": data["total_reviews"],
            "avg_swipe_ms": avg_ms,
            "avg_score": avg_score,
            "flagged_fast_count": data["flagged_fast_count"],
            "flagged_fast_pct": flagged_pct,
            "rating_distribution": data["rating_distribution"],
            "calibration_drift": avg_drift,
            "drift_direction": drift_direction,
            "speed_trend": speed_trend,
        })

    reviewers.sort(key=lambda x: x["total_reviews"], reverse=True)

    return {
        "period_days": days,
        "reviewer_count": len(reviewers),
        "reviewers": reviewers,
    }

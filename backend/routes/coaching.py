import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, utc_now, audit_entry,
    build_repeat_offender_summary, select_training_snapshots,
    create_notification,
)

router = APIRouter()


@router.get("/coaching/recommendations")
async def get_coaching_recommendations(
    user: dict = Depends(require_roles("management", "owner")),
    window_days: int = Query(30, ge=1, le=365),
):
    """Return auto-coaching recommendations for crews at Warning or Critical level."""
    summary = await build_repeat_offender_summary(window_days, (3, 5, 7))
    recommendations = []

    for crew in summary["crew_summaries"]:
        if crew["level"] not in ("Warning", "Critical"):
            continue

        # Determine top issue types for targeted training
        sorted_issues = sorted(crew["issue_types"].items(), key=lambda x: x[1], reverse=True)
        top_issues = [issue for issue, _ in sorted_issues[:3]]

        recommendations.append({
            "crew": crew["crew"],
            "access_code": crew.get("access_code", ""),
            "division": crew.get("division", ""),
            "level": crew["level"],
            "incident_count": crew["incident_count"],
            "top_issues": top_issues,
            "recommended_action": "Full retraining + ride-along" if crew["level"] == "Critical" else "Focused corrective training",
            "suggested_item_count": 5 if crew["level"] == "Critical" else 3,
        })

    recommendations.sort(key=lambda x: x["incident_count"], reverse=True)
    return {"window_days": window_days, "recommendations": recommendations}


@router.post("/coaching/auto-generate")
async def auto_generate_coaching(
    user: dict = Depends(require_roles("management", "owner")),
    window_days: int = Query(30, ge=1, le=365),
):
    """Auto-generate training sessions for all crews at Warning/Critical levels."""
    summary = await build_repeat_offender_summary(window_days, (3, 5, 7))
    created_sessions = []
    skipped = []

    for crew in summary["crew_summaries"]:
        if crew["level"] not in ("Warning", "Critical"):
            continue

        access_code = crew.get("access_code", "")
        if not access_code:
            skipped.append({"crew": crew["crew"], "reason": "No access code linked"})
            continue

        # Check if crew already has an active session generated recently
        existing = await deps.db.training_sessions.find_one(
            {"access_code": access_code, "status": "active", "coaching_generated": True},
            {"_id": 0, "id": 1, "created_at": 1},
        )
        if existing:
            skipped.append({"crew": crew["crew"], "reason": "Active coaching session already exists"})
            continue

        division = crew.get("division", "")
        item_count = 5 if crew["level"] == "Critical" else 3

        # Select training items, preferring those matching top issue types
        snapshots = await select_training_snapshots(division, item_count)
        if not snapshots:
            skipped.append({"crew": crew["crew"], "reason": "No eligible training standards"})
            continue

        code = f"COACH{uuid.uuid4().hex[:8].upper()}"
        sorted_issues = sorted(crew["issue_types"].items(), key=lambda x: x[1], reverse=True)
        top_issues = [issue for issue, _ in sorted_issues[:3]]

        session = {
            "id": make_id("coach"),
            "code": code,
            "crew_link_id": "",
            "crew_label": crew["crew"],
            "access_code": access_code,
            "division": division,
            "item_count": len(snapshots),
            "items": snapshots,
            "status": "active",
            "score_percent": None,
            "completion_rate": None,
            "average_time_seconds": None,
            "coaching_generated": True,
            "coaching_level": crew["level"],
            "coaching_top_issues": top_issues,
            "coaching_incident_count": crew["incident_count"],
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await deps.db.training_sessions.insert_one({**session})
        created_sessions.append({
            "crew": crew["crew"],
            "level": crew["level"],
            "session_id": session["id"],
            "session_code": code,
            "item_count": len(snapshots),
            "top_issues": top_issues,
        })

    # Notify owner/GM about generated coaching sessions
    if created_sessions:
        crew_list = ", ".join(s["crew"] for s in created_sessions)
        await create_notification(
            title="Auto-coaching sessions generated",
            message=f"{len(created_sessions)} coaching session(s) created for: {crew_list}.",
            audience="admin",
            target_titles=["Owner", "GM"],
            notification_type="coaching",
        )

    return {
        "generated": len(created_sessions),
        "skipped": len(skipped),
        "sessions": created_sessions,
        "skipped_details": skipped,
    }



@router.get("/coaching/score-analysis")
async def score_based_analysis(
    user: dict = Depends(require_roles("management", "owner")),
    window_days: int = Query(90, ge=7, le=365),
    division: str = Query("all"),
):
    """Analyze crew scores by task/rubric category to find weak areas for targeted coaching."""
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()

    # Get all rapid reviews in window
    rr_query = {"created_at": {"$gte": cutoff}}
    rapid_reviews = await deps.db.rapid_reviews.find(rr_query, {"_id": 0}).to_list(5000)

    if not rapid_reviews:
        return {"window_days": window_days, "crews": [], "division_summary": {}}

    # Map submission_id -> crew info
    sub_ids = [r["submission_id"] for r in rapid_reviews]
    sub_query = {"id": {"$in": sub_ids}}
    if division != "all":
        sub_query["division"] = division
    subs = await deps.db.submissions.find(sub_query, {
        "_id": 0, "id": 1, "access_code": 1, "crew_label": 1, "division": 1, "service_type": 1, "member_code": 1,
    }).to_list(5000)
    sub_map = {s["id"]: s for s in subs}

    # Build per-crew, per-task score aggregation
    crew_scores = {}  # {crew_code: {task: {ratings: [], sum_pcts: [], count: 0}}}

    for rr in rapid_reviews:
        sub = sub_map.get(rr["submission_id"])
        if not sub:
            continue
        code = sub["access_code"]
        task = sub.get("service_type", "unknown")
        label = sub.get("crew_label", "Unknown Crew")
        div = sub.get("division", "Unknown")

        crew = crew_scores.setdefault(code, {"label": label, "division": div, "tasks": {}})
        t = crew["tasks"].setdefault(task, {"ratings": [], "sum_pcts": [], "count": 0})
        t["ratings"].append(rr.get("overall_rating", "standard"))
        t["sum_pcts"].append(rr.get("rubric_sum_percent", 0))
        t["count"] += 1

    # Compute summary per crew
    RATING_WEIGHTS = {"fail": 0, "concern": 25, "standard": 72, "exemplary": 100}
    result_crews = []

    for code, data in crew_scores.items():
        task_summaries = []
        all_weighted = []

        for task, scores in data["tasks"].items():
            weighted = [RATING_WEIGHTS.get(r, 50) for r in scores["ratings"]]
            avg_rating = round(sum(weighted) / len(weighted), 1) if weighted else 0
            avg_pct = round(sum(scores["sum_pcts"]) / len(scores["sum_pcts"]), 1) if scores["sum_pcts"] else 0
            fail_count = scores["ratings"].count("fail")
            concern_count = scores["ratings"].count("concern")

            task_summaries.append({
                "task": task,
                "review_count": scores["count"],
                "avg_rating_score": avg_rating,
                "avg_rubric_pct": avg_pct,
                "fail_count": fail_count,
                "concern_count": concern_count,
                "needs_coaching": fail_count > 0 or concern_count > 0 or avg_rating < 60,
            })
            all_weighted.extend(weighted)

        task_summaries.sort(key=lambda x: x["avg_rating_score"])
        overall_avg = round(sum(all_weighted) / len(all_weighted), 1) if all_weighted else 0
        weak_tasks = [t for t in task_summaries if t["needs_coaching"]]

        result_crews.append({
            "crew_code": code,
            "crew_label": data["label"],
            "division": data["division"],
            "overall_avg_score": overall_avg,
            "total_reviews": sum(t["review_count"] for t in task_summaries),
            "task_breakdown": task_summaries,
            "weak_tasks": weak_tasks,
            "coaching_priority": "high" if len(weak_tasks) >= 2 or overall_avg < 50 else "medium" if weak_tasks else "low",
        })

    result_crews.sort(key=lambda x: x["overall_avg_score"])

    # Division-level summary
    div_summary = {}
    for crew in result_crews:
        d = crew["division"]
        entry = div_summary.setdefault(d, {"total_crews": 0, "avg_score": 0, "total_reviews": 0, "high_priority": 0})
        entry["total_crews"] += 1
        entry["avg_score"] += crew["overall_avg_score"]
        entry["total_reviews"] += crew["total_reviews"]
        if crew["coaching_priority"] == "high":
            entry["high_priority"] += 1

    for d, entry in div_summary.items():
        if entry["total_crews"]:
            entry["avg_score"] = round(entry["avg_score"] / entry["total_crews"], 1)

    return {
        "window_days": window_days,
        "division_filter": division,
        "crews": result_crews,
        "division_summary": div_summary,
    }

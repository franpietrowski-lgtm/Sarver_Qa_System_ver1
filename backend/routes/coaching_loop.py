"""Closed-loop coaching completion reports.

Links repeat offenders → coaching actions → training sessions → resolution.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Body

import shared.deps as deps
from shared.deps import require_roles, now_iso, make_id

router = APIRouter()


@router.get("/coaching/loop-report")
async def coaching_loop_report(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = Query("all"),
):
    """Full closed-loop report: offenders → assigned coaching → completion status."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=180)).isoformat()

    # Find repeat offenders (crews with 3+ flagged issues in 180 days)
    subs_query = {"created_at": {"$gte": cutoff}}
    if division != "all":
        subs_query["division"] = division
    subs = await deps.db.submissions.find(subs_query, {"_id": 0, "id": 1, "access_code": 1, "crew_label": 1, "division": 1}).to_list(5000)
    sub_ids = [s["id"] for s in subs]
    reviews = await deps.db.management_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}, "flagged_issues": {"$exists": True, "$ne": []}},
        {"_id": 0, "submission_id": 1, "flagged_issues": 1, "created_at": 1}
    ).to_list(5000)
    rapid = await deps.db.rapid_reviews.find(
        {"submission_id": {"$in": sub_ids or ["__none__"]}, "overall_rating": {"$in": ["fail", "concern"]}},
        {"_id": 0, "submission_id": 1, "issue_tag": 1, "created_at": 1}
    ).to_list(5000)

    sub_crew_map = {s["id"]: {"code": s["access_code"], "label": s.get("crew_label", ""), "division": s.get("division", "")} for s in subs}
    crew_issues = {}
    for rev in reviews:
        crew_info = sub_crew_map.get(rev["submission_id"])
        if not crew_info:
            continue
        key = crew_info["code"]
        entry = crew_issues.setdefault(key, {"label": crew_info["label"], "division": crew_info["division"], "issues": [], "issue_tags": {}})
        for issue in rev.get("flagged_issues", []):
            entry["issues"].append({"tag": issue, "date": rev.get("created_at"), "source": "review"})
            entry["issue_tags"][issue] = entry["issue_tags"].get(issue, 0) + 1
    for rr in rapid:
        crew_info = sub_crew_map.get(rr["submission_id"])
        if not crew_info:
            continue
        key = crew_info["code"]
        entry = crew_issues.setdefault(key, {"label": crew_info["label"], "division": crew_info["division"], "issues": [], "issue_tags": {}})
        tag = rr.get("issue_tag", "unspecified")
        entry["issues"].append({"tag": tag, "date": rr.get("created_at"), "source": "rapid"})
        entry["issue_tags"][tag] = entry["issue_tags"].get(tag, 0) + 1

    # Get coaching records
    coaching_records = await deps.db.coaching_actions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0}
    ).to_list(500)
    coaching_by_crew = {}
    for c in coaching_records:
        coaching_by_crew.setdefault(c.get("crew_code", ""), []).append(c)

    # Get training sessions
    training_records = await deps.db.training_sessions.find(
        {"created_at": {"$gte": cutoff}},
        {"_id": 0, "access_code": 1, "status": 1, "score": 1, "created_at": 1}
    ).to_list(500)
    training_by_crew = {}
    for t in training_records:
        training_by_crew.setdefault(t.get("access_code", ""), []).append(t)

    # Build report
    report = []
    for code, data in crew_issues.items():
        total_issues = len(data["issues"])
        if total_issues < 2:
            continue  # Not a repeat offender

        coaching = coaching_by_crew.get(code, [])
        training = training_by_crew.get(code, [])
        coaching_assigned = len(coaching)
        coaching_completed = sum(1 for c in coaching if c.get("status") == "completed")
        training_completed = sum(1 for t in training if t.get("status") == "completed")

        # Determine loop status
        if coaching_completed > 0 and training_completed > 0:
            loop_status = "closed"
        elif coaching_assigned > 0:
            loop_status = "in_progress"
        else:
            loop_status = "open"

        top_issues = sorted(data["issue_tags"].items(), key=lambda x: x[1], reverse=True)[:5]

        report.append({
            "crew_code": code,
            "crew_label": data["label"],
            "division": data["division"],
            "total_issues": total_issues,
            "top_issues": [{"tag": tag, "count": ct} for tag, ct in top_issues],
            "coaching_assigned": coaching_assigned,
            "coaching_completed": coaching_completed,
            "training_sessions": len(training),
            "training_completed": training_completed,
            "loop_status": loop_status,
        })

    report.sort(key=lambda x: x["total_issues"], reverse=True)

    return {
        "report": report,
        "summary": {
            "total_offenders": len(report),
            "closed_loops": sum(1 for r in report if r["loop_status"] == "closed"),
            "in_progress": sum(1 for r in report if r["loop_status"] == "in_progress"),
            "open_loops": sum(1 for r in report if r["loop_status"] == "open"),
        }
    }


@router.post("/coaching/assign")
async def assign_coaching(
    user: dict = Depends(require_roles("management", "owner")),
    payload: dict = Body(...),
):
    """Assign a coaching action to a crew."""
    crew_code = payload.get("crew_code", "")
    issue_tags = payload.get("issue_tags", [])
    notes = payload.get("notes", "")

    if not crew_code:
        return {"error": "crew_code required"}

    action = {
        "id": make_id("coach"),
        "crew_code": crew_code,
        "assigned_by": user.get("id", ""),
        "assigned_by_name": user.get("name", ""),
        "issue_tags": issue_tags,
        "notes": notes,
        "status": "assigned",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await deps.db.coaching_actions.insert_one(action)
    del action["_id"]
    return action


@router.patch("/coaching/{action_id}/complete")
async def complete_coaching(
    action_id: str,
    user: dict = Depends(require_roles("management", "owner")),
    payload: dict = Body({}),
):
    """Mark a coaching action as completed."""
    result = await deps.db.coaching_actions.find_one_and_update(
        {"id": action_id},
        {"$set": {
            "status": "completed",
            "completed_by": user.get("id", ""),
            "completed_by_name": user.get("name", ""),
            "completion_notes": payload.get("notes", ""),
            "updated_at": now_iso(),
        }},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        return {"error": "Coaching action not found"}
    return result

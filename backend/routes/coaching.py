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

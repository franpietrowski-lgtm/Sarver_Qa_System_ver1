"""Onboarding progress tracker for crew members."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

import shared.deps as deps
from shared.deps import require_roles, now_iso, make_id

router = APIRouter()

MILESTONES = [
    {"key": "first_submission", "label": "First Submission", "description": "Crew submits their first field work capture"},
    {"key": "first_review", "label": "First Review", "description": "First submission gets reviewed by management"},
    {"key": "training_started", "label": "Training Started", "description": "Crew member begins a training session"},
    {"key": "training_completed", "label": "Training Passed", "description": "Crew member passes a training session"},
    {"key": "equipment_check", "label": "Equipment Check", "description": "First equipment maintenance log filed"},
    {"key": "five_submissions", "label": "5 Submissions", "description": "Crew reaches 5 total field submissions"},
]


@router.get("/onboarding/progress")
async def onboarding_progress(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = Query("all"),
):
    """Get onboarding progress for all crews."""
    crew_query = {"enabled": True}
    if division != "all":
        crew_query["division"] = division
    crews = await deps.db.crew_access_links.find(crew_query, {"_id": 0, "code": 1, "label": 1, "leader_name": 1, "division": 1, "created_at": 1}).to_list(50)

    results = []
    for crew in crews:
        code = crew["code"]
        milestones = {}

        # First submission
        first_sub = await deps.db.submissions.find_one(
            {"access_code": code}, {"_id": 0, "id": 1, "created_at": 1},
            sort=[("created_at", 1)]
        )
        milestones["first_submission"] = {"done": bool(first_sub), "date": first_sub["created_at"] if first_sub else None}

        # First review
        if first_sub:
            sub_ids = [s["id"] for s in await deps.db.submissions.find({"access_code": code}, {"_id": 0, "id": 1}).to_list(500)]
            first_rev = await deps.db.management_reviews.find_one(
                {"submission_id": {"$in": sub_ids or ["__none__"]}},
                {"_id": 0, "created_at": 1}, sort=[("created_at", 1)]
            )
            milestones["first_review"] = {"done": bool(first_rev), "date": first_rev["created_at"] if first_rev else None}
        else:
            sub_ids = []
            milestones["first_review"] = {"done": False, "date": None}

        # Training started
        train_any = await deps.db.training_sessions.find_one(
            {"access_code": code}, {"_id": 0, "created_at": 1}, sort=[("created_at", 1)]
        )
        milestones["training_started"] = {"done": bool(train_any), "date": train_any["created_at"] if train_any else None}

        # Training completed
        train_done = await deps.db.training_sessions.find_one(
            {"access_code": code, "status": "completed"}, {"_id": 0, "created_at": 1}, sort=[("created_at", 1)]
        )
        milestones["training_completed"] = {"done": bool(train_done), "date": train_done["created_at"] if train_done else None}

        # Equipment check
        equip = await deps.db.equipment_logs.find_one(
            {"access_code": code}, {"_id": 0, "created_at": 1}, sort=[("created_at", 1)]
        )
        milestones["equipment_check"] = {"done": bool(equip), "date": equip["created_at"] if equip else None}

        # 5 submissions
        sub_count = await deps.db.submissions.count_documents({"access_code": code})
        milestones["five_submissions"] = {"done": sub_count >= 5, "date": None, "count": sub_count}

        completed = sum(1 for m in milestones.values() if m["done"])
        results.append({
            "crew_label": crew.get("label", ""),
            "leader_name": crew.get("leader_name", ""),
            "division": crew.get("division", ""),
            "created_at": crew.get("created_at", ""),
            "milestones": milestones,
            "completed_count": completed,
            "total_milestones": len(MILESTONES),
            "progress_pct": round((completed / len(MILESTONES)) * 100),
        })

    results.sort(key=lambda x: x["progress_pct"])
    return {"crews": results, "milestone_definitions": MILESTONES}

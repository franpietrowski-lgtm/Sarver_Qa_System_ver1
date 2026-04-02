import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso,
    normalize_page, normalize_limit,
    build_repeat_offender_summary, get_recent_training_sessions,
    select_training_snapshots,
)
from shared.models import TrainingSessionCreateRequest

router = APIRouter()


@router.get("/repeat-offenders")
async def get_repeat_offenders(
    user: dict = Depends(require_roles("management", "owner")),
    window_days: int = Query(30, ge=1, le=365),
    threshold_one: int = Query(3, ge=1, le=20),
    threshold_two: int = Query(5, ge=1, le=30),
    threshold_three: int = Query(7, ge=1, le=50),
):
    return await build_repeat_offender_summary(window_days, (threshold_one, threshold_two, threshold_three))


@router.get("/training-sessions")
async def get_training_sessions(
    user: dict = Depends(require_roles("management", "owner")),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    return await get_recent_training_sessions(page, limit)


@router.post("/training-sessions", status_code=201)
async def create_training_session(
    payload: TrainingSessionCreateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    crew_link = await deps.db.crew_access_links.find_one({"code": payload.access_code}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    division = payload.division or crew_link.get("division", "")
    snapshots = await select_training_snapshots(division, max(1, min(payload.item_count, 5)))
    if not snapshots:
        raise HTTPException(status_code=400, detail="No training-ready standards match this division yet")
    code = f"TRAIN{uuid.uuid4().hex[:8].upper()}"
    session = {
        "id": make_id("train"),
        "code": code,
        "crew_link_id": crew_link["id"],
        "crew_label": crew_link.get("label", "Crew"),
        "access_code": crew_link["code"],
        "division": division,
        "item_count": len(snapshots),
        "items": snapshots,
        "status": "active",
        "score_percent": None,
        "completion_rate": None,
        "average_time_seconds": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    response_session = {**session}
    await deps.db.training_sessions.insert_one(session)
    return {**response_session, "session_url": f"{os.environ['FRONTEND_URL']}/training/{code}"}

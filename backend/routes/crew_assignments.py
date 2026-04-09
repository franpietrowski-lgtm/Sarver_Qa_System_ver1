"""Daily Crew Assignment — Job-to-Crew mapping for PMs.

Supports:
  - GET /crew-assignments?date=YYYY-MM-DD  — Fetch day's assignments
  - GET /crew-assignments/week?start=YYYY-MM-DD — Fetch week forecast
  - POST /crew-assignments — Create/update a single assignment
  - POST /crew-assignments/bulk — Bulk assign (drag-drop or week preload)
  - DELETE /crew-assignments/{assignment_id} — Remove assignment
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Body, HTTPException

import shared.deps as deps
from shared.deps import require_roles, make_id, now_iso

router = APIRouter()


@router.get("/crew-assignments")
async def get_crew_assignments(
    user: dict = Depends(require_roles("management", "owner")),
    date: str = Query(None, description="YYYY-MM-DD"),
):
    """Fetch assignments for a given date (defaults to today)."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    assignments = await deps.db.crew_assignments.find(
        {"date": date}, {"_id": 0}
    ).sort("created_at", 1).to_list(200)

    # Enrich with crew and job info
    crew_codes = list({a["crew_code"] for a in assignments})
    job_ids = list({a["job_id"] for a in assignments})

    crews = {}
    if crew_codes:
        async for c in deps.db.crew_access_links.find({"code": {"$in": crew_codes}}, {"_id": 0}):
            crews[c["code"]] = {"label": c.get("label", ""), "division": c.get("division", ""), "truck_number": c.get("truck_number", ""), "leader_name": c.get("leader_name", "")}

    jobs = {}
    if job_ids:
        async for j in deps.db.jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0, "job_id": 1, "job_name": 1, "property_name": 1, "service_type": 1, "address": 1, "division": 1, "route": 1}):
            jobs[j["job_id"]] = j

    for a in assignments:
        a["crew"] = crews.get(a["crew_code"], {})
        a["job"] = jobs.get(a["job_id"], {})

    return {"date": date, "assignments": assignments}


@router.get("/crew-assignments/week")
async def get_week_assignments(
    user: dict = Depends(require_roles("management", "owner")),
    start: str = Query(None, description="YYYY-MM-DD, defaults to Monday of current week"),
):
    """Fetch a full work week (Mon-Fri) of assignments."""
    if start:
        start_date = datetime.strptime(start, "%Y-%m-%d")
    else:
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=today.weekday())

    dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    assignments = await deps.db.crew_assignments.find(
        {"date": {"$in": dates}}, {"_id": 0}
    ).sort([("date", 1), ("created_at", 1)]).to_list(500)

    # Enrich
    crew_codes = list({a["crew_code"] for a in assignments})
    job_ids = list({a["job_id"] for a in assignments})

    crews = {}
    if crew_codes:
        async for c in deps.db.crew_access_links.find({"code": {"$in": crew_codes}}, {"_id": 0}):
            crews[c["code"]] = {"label": c.get("label", ""), "division": c.get("division", ""), "truck_number": c.get("truck_number", ""), "leader_name": c.get("leader_name", "")}

    jobs = {}
    if job_ids:
        async for j in deps.db.jobs.find({"job_id": {"$in": job_ids}}, {"_id": 0, "job_id": 1, "job_name": 1, "property_name": 1, "service_type": 1, "address": 1, "division": 1, "route": 1}):
            jobs[j["job_id"]] = j

    week = {}
    for d in dates:
        week[d] = []

    for a in assignments:
        a["crew"] = crews.get(a["crew_code"], {})
        a["job"] = jobs.get(a["job_id"], {})
        week.setdefault(a["date"], []).append(a)

    return {"start": dates[0], "end": dates[-1], "dates": dates, "week": week}


@router.post("/crew-assignments")
async def create_assignment(
    user: dict = Depends(require_roles("management", "owner")),
    payload: dict = Body(...),
):
    """Create a single crew-to-job assignment for a date."""
    crew_code = payload.get("crew_code", "")
    job_id = payload.get("job_id", "")
    date = payload.get("date", "")
    priority = payload.get("priority", "normal")
    notes = payload.get("notes", "")

    if not crew_code or not job_id or not date:
        raise HTTPException(status_code=400, detail="crew_code, job_id, and date are required")

    # Prevent duplicates
    existing = await deps.db.crew_assignments.find_one(
        {"crew_code": crew_code, "job_id": job_id, "date": date}, {"_id": 0, "id": 1}
    )
    if existing:
        raise HTTPException(status_code=409, detail="This crew is already assigned to this job on this date")

    assignment = {
        "id": make_id("assign"),
        "crew_code": crew_code,
        "job_id": job_id,
        "date": date,
        "priority": priority,
        "notes": notes,
        "assigned_by": user.get("id", ""),
        "assigned_by_name": user.get("name", ""),
        "status": "scheduled",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await deps.db.crew_assignments.insert_one({**assignment})
    return assignment


@router.post("/crew-assignments/bulk")
async def bulk_assign(
    user: dict = Depends(require_roles("management", "owner")),
    payload: dict = Body(...),
):
    """Bulk create assignments. Expects {assignments: [{crew_code, job_id, date, priority?, notes?}]}."""
    items = payload.get("assignments", [])
    if not items:
        raise HTTPException(status_code=400, detail="No assignments provided")

    created = []
    skipped = []
    for item in items:
        crew_code = item.get("crew_code", "")
        job_id = item.get("job_id", "")
        date = item.get("date", "")
        if not crew_code or not job_id or not date:
            skipped.append({"item": item, "reason": "Missing required fields"})
            continue

        existing = await deps.db.crew_assignments.find_one(
            {"crew_code": crew_code, "job_id": job_id, "date": date}, {"_id": 0, "id": 1}
        )
        if existing:
            skipped.append({"item": item, "reason": "Already assigned"})
            continue

        assignment = {
            "id": make_id("assign"),
            "crew_code": crew_code,
            "job_id": job_id,
            "date": date,
            "priority": item.get("priority", "normal"),
            "notes": item.get("notes", ""),
            "assigned_by": user.get("id", ""),
            "assigned_by_name": user.get("name", ""),
            "status": "scheduled",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await deps.db.crew_assignments.insert_one({**assignment})
        created.append(assignment)

    return {"created": len(created), "skipped": len(skipped), "assignments": created, "skipped_details": skipped}


@router.delete("/crew-assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    """Remove a crew assignment."""
    result = await deps.db.crew_assignments.delete_one({"id": assignment_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"deleted": True, "id": assignment_id}

import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import shared.deps as deps
from shared.deps import make_id, now_iso, audit_entry, select_training_snapshots, match_training_answer

router = APIRouter()


class CrewMemberRegisterRequest(BaseModel):
    name: str
    division: str
    parent_access_code: str


@router.post("/public/crew-members/register")
async def register_crew_member(payload: CrewMemberRegisterRequest):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    parent = await deps.db.crew_access_links.find_one(
        {"code": payload.parent_access_code, "enabled": True}, {"_id": 0}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Crew link not found or inactive")

    member_code = uuid.uuid4().hex[:8]
    member = {
        "id": make_id("cm"),
        "code": member_code,
        "name": name,
        "division": payload.division or parent.get("division", ""),
        "parent_access_code": payload.parent_access_code,
        "parent_crew_label": parent.get("label", ""),
        "parent_truck_number": parent.get("truck_number", ""),
        "active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("registered", member_code, f"Crew member '{name}' self-registered")],
    }
    await deps.db.crew_members.insert_one({**member})
    return {
        "code": member_code,
        "name": name,
        "division": member["division"],
        "parent_crew_label": member["parent_crew_label"],
    }


@router.get("/public/crew-member/{code}")
async def get_crew_member(code: str):
    member = await deps.db.crew_members.find_one({"code": code, "active": True}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return {
        "code": member["code"],
        "name": member["name"],
        "division": member["division"],
        "parent_crew_label": member.get("parent_crew_label", ""),
        "parent_truck_number": member.get("parent_truck_number", ""),
        "parent_access_code": member.get("parent_access_code", ""),
        "created_at": member.get("created_at", ""),
    }


@router.get("/public/crew-member/{code}/standards")
async def get_crew_member_standards(code: str):
    member = await deps.db.crew_members.find_one({"code": code, "active": True}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    query = {"is_active": True}
    standards = await deps.db.standards_library.find(query, {"_id": 0}).to_list(100)
    division = member.get("division", "")
    filtered = []
    for s in standards:
        targets = s.get("division_targets", [])
        if not targets or division in targets:
            filtered.append({
                "id": s["id"],
                "title": s["title"],
                "category": s.get("category", ""),
                "image_url": s.get("image_url", ""),
                "notes": s.get("notes", ""),
                "checklist": s.get("checklist", []),
                "shoutout": s.get("shoutout", ""),
            })
    return {"standards": filtered, "division": division}


@router.get("/public/crew-member/{code}/training")
async def get_crew_member_training(code: str):
    member = await deps.db.crew_members.find_one({"code": code, "active": True}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    sessions = await deps.db.training_sessions.find(
        {"access_code": member.get("parent_access_code", "")},
        {"_id": 0},
    ).sort("created_at", -1).to_list(50)
    result = []
    for s in sessions:
        result.append({
            "code": s["code"],
            "crew_label": s.get("crew_label", ""),
            "division": s.get("division", ""),
            "item_count": s.get("item_count", 0),
            "status": s.get("status", "pending"),
            "score_percent": s.get("score_percent"),
            "created_at": s.get("created_at", ""),
            "completed_at": s.get("completed_at"),
        })
    return {"training_sessions": result}


@router.get("/public/crew-member/{code}/submissions")
async def get_crew_member_submissions(code: str, page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50)):
    member = await deps.db.crew_members.find_one({"code": code, "active": True}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Crew member not found")
    query = {"member_code": code}
    total = await deps.db.submissions.count_documents(query)
    submissions = (
        await deps.db.submissions.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    items = []
    for s in submissions:
        items.append({
            "id": s["id"],
            "job_name_input": s.get("job_name_input", ""),
            "task_type": s.get("task_type", ""),
            "status": s.get("status", ""),
            "work_date": s.get("work_date", ""),
            "photo_count": s.get("photo_count", 0),
            "created_at": s.get("created_at", ""),
        })
    return {"submissions": items, "total": total, "page": page, "limit": limit}


@router.get("/public/crew-member-stats/{parent_access_code}")
async def get_crew_member_stats(parent_access_code: str):
    parent = await deps.db.crew_access_links.find_one(
        {"code": parent_access_code, "enabled": True}, {"_id": 0}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Crew link not found")
    members = await deps.db.crew_members.find(
        {"parent_access_code": parent_access_code, "active": True}, {"_id": 0}
    ).to_list(100)
    result = []
    for m in members:
        sub_count = await deps.db.submissions.count_documents({"member_code": m["code"]})
        training_sessions = await deps.db.training_sessions.find(
            {"access_code": parent_access_code}, {"_id": 0, "status": 1}
        ).to_list(100)
        total_training = len(training_sessions)
        completed_training = sum(1 for t in training_sessions if t.get("status") == "completed")
        result.append({
            "code": m["code"],
            "name": m["name"],
            "division": m.get("division", ""),
            "submission_count": sub_count,
            "training_total": total_training,
            "training_completed": completed_training,
            "created_at": m.get("created_at", ""),
        })
    return {"members": result, "crew_label": parent.get("label", "")}
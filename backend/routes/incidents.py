"""Incident & emergency reporting routes — active incidents feed for Overview."""
from fastapi import APIRouter, Depends

import shared.deps as deps
from shared.deps import require_roles

router = APIRouter()


@router.get("/incidents/active")
async def get_active_incidents(
    user: dict = Depends(require_roles("management", "owner")),
):
    """Return recent emergency submissions for the Overview alert widget."""
    pipeline = [
        {"$match": {"is_emergency": True, "incident_acknowledged": {"$ne": True}}},
        {"$sort": {"created_at": -1}},
        {"$limit": 50},
        {"$project": {
            "_id": 0,
            "id": 1,
            "submission_code": 1,
            "crew_label": 1,
            "job_name_input": 1,
            "division": 1,
            "truck_number": 1,
            "work_date": 1,
            "note": 1,
            "field_report": 1,
            "gps": 1,
            "is_emergency": 1,
            "status": 1,
            "created_at": 1,
            "member_code": 1,
            "access_code": 1,
        }},
    ]
    docs = await deps.db.submissions.aggregate(pipeline).to_list(50)
    return {"incidents": docs, "total": len(docs)}


@router.get("/incidents/{incident_id}")
async def get_incident_detail(
    incident_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    """Full detail for a single emergency incident."""
    doc = await deps.db.submissions.find_one(
        {"id": incident_id, "is_emergency": True},
        {"_id": 0},
    )
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")
    return doc


@router.patch("/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(
    incident_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    """Mark an emergency incident as acknowledged/read by an admin."""
    result = await deps.db.submissions.update_one(
        {"id": incident_id, "is_emergency": True},
        {
            "$set": {"incident_acknowledged": True, "acknowledged_by": user["id"], "acknowledged_at": deps.now_iso()},
            "$push": {"audit_history": deps.audit_entry("incident_acknowledged", user["id"], f"Acknowledged by {user.get('name','admin')}")},
        },
    )
    if result.matched_count == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"acknowledged": True, "incident_id": incident_id}


@router.get("/rubrics/for-task")
async def get_rubric_for_task(
    service_type: str = "",
    division: str = "",
    user: dict = Depends(require_roles("management", "owner")),
):
    """Get rubric criteria relevant to a specific task type for rapid review guidance."""
    query = {"is_active": True}
    if service_type:
        query["service_type"] = service_type.lower()
    if division and division != "all":
        query["division"] = division
    rubrics = await deps.db.rubric_definitions.find(query, {"_id": 0}).to_list(10)
    if not rubrics and service_type:
        rubrics = await deps.db.rubric_definitions.find({"is_active": True}, {"_id": 0}).to_list(10)
    categories = []
    for r in rubrics:
        hf = r.get("hard_fail_conditions", [])
        for cat in r.get("categories", []):
            label = cat.get("label", cat.get("name", cat.get("key", "")))
            categories.append({
                "name": label,
                "key": cat.get("key", ""),
                "weight": cat.get("weight", 0),
                "max_score": cat.get("max_score", 5),
                "criteria": cat.get("criteria", [f"Score {label} from 1-{cat.get('max_score',5)}"]),
                "fail_indicators": cat.get("fail_indicators", [f"Poor {label}", *[h.replace("_", " ").title() for h in hf[:2]]]),
                "exemplary_indicators": cat.get("exemplary_indicators", [f"Outstanding {label}", f"Exceeds {label} standard"]),
                "division": r.get("division", ""),
                "service_type": r.get("service_type", ""),
            })
    return {"rubric_categories": categories, "rubric_count": len(rubrics), "hard_fail_conditions": rubrics[0].get("hard_fail_conditions", []) if rubrics else []}

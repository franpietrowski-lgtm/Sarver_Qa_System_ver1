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
        {"$match": {"is_emergency": True}},
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

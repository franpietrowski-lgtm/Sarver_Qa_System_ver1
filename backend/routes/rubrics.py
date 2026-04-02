from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry, serialize,
)
from shared.models import RubricMatrixCreate, RubricMatrixUpdate

router = APIRouter()


@router.get("/rubrics")
async def get_rubrics(user: dict = Depends(require_roles("management", "owner"))):
    rubrics = await deps.db.rubric_definitions.find({"is_active": True}, {"_id": 0}).sort("service_type", 1).to_list(50)
    return rubrics


@router.get("/rubric-matrices")
async def get_rubric_matrices(
    user: dict = Depends(require_roles("management", "owner")),
    division: str = "all",
    service_type: str = "all",
    include_inactive: bool = False,
):
    query: dict[str, Any] = {}
    if not include_inactive:
        query["is_active"] = True
    if division != "all":
        query["division"] = division
    if service_type != "all":
        query["service_type"] = service_type.lower()
    rubrics = await deps.db.rubric_definitions.find(query, {"_id": 0}).sort([("division", 1), ("service_type", 1)]).to_list(200)
    return rubrics


@router.post("/rubric-matrices", status_code=201)
async def create_rubric_matrix(
    payload: RubricMatrixCreate,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can create rubric matrices")
    existing = await deps.db.rubric_definitions.find_one(
        {"service_type": payload.service_type.lower(), "division": payload.division, "is_active": True}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Active rubric already exists for {payload.service_type} in {payload.division}")
    max_version_doc = await deps.db.rubric_definitions.find_one(
        {"service_type": payload.service_type.lower()}, {"version": 1, "_id": 0}, sort=[("version", -1)]
    )
    next_version = (max_version_doc["version"] + 1) if max_version_doc else 1
    rubric_id = make_id("rubric")
    document = {
        "id": rubric_id,
        "service_type": payload.service_type.lower(),
        "division": payload.division,
        "title": payload.title,
        "version": next_version,
        "min_photos": payload.min_photos,
        "pass_threshold": payload.pass_threshold,
        "hard_fail_conditions": payload.hard_fail_conditions,
        "categories": [cat.model_dump() for cat in payload.categories],
        "is_active": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], f"Rubric matrix created by {user['title']}")],
    }
    await deps.db.rubric_definitions.insert_one(document)
    document.pop("_id", None)
    return document


@router.patch("/rubric-matrices/{rubric_id}")
async def update_rubric_matrix(
    rubric_id: str,
    payload: RubricMatrixUpdate,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can update rubric matrices")
    existing = await deps.db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rubric matrix not found")
    updates: dict[str, Any] = {"updated_at": now_iso()}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.division is not None:
        updates["division"] = payload.division
    if payload.min_photos is not None:
        updates["min_photos"] = payload.min_photos
    if payload.pass_threshold is not None:
        updates["pass_threshold"] = payload.pass_threshold
    if payload.hard_fail_conditions is not None:
        updates["hard_fail_conditions"] = payload.hard_fail_conditions
    if payload.categories is not None:
        updates["categories"] = [cat.model_dump() for cat in payload.categories]
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
    await deps.db.rubric_definitions.update_one(
        {"id": rubric_id},
        {
            "$set": updates,
            "$push": {"audit_history": audit_entry("updated", user["id"], f"Rubric updated by {user['title']}")},
        },
    )
    updated = await deps.db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    return serialize(updated)


@router.delete("/rubric-matrices/{rubric_id}")
async def delete_rubric_matrix(
    rubric_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    if user.get("title") not in ("GM", "Owner"):
        raise HTTPException(status_code=403, detail="Only GM or Owner can delete rubric matrices")
    existing = await deps.db.rubric_definitions.find_one({"id": rubric_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rubric matrix not found")
    await deps.db.rubric_definitions.update_one(
        {"id": rubric_id},
        {
            "$set": {"is_active": False, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("deactivated", user["id"], f"Rubric deactivated by {user['title']}")},
        },
    )
    return {"ok": True, "detail": "Rubric matrix deactivated"}

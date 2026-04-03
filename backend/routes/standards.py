from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso,
    normalize_page, normalize_limit, build_paginated_response,
)
from shared.models import StandardItemRequest, StandardItemUpdateRequest

router = APIRouter()


@router.get("/standards")
async def get_standards(
    user: dict = Depends(require_roles("management", "owner")),
    search: str = "",
    category: str = "all",
    division: str = "all",
    audience: str = "all",
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
):
    query: dict[str, Any] = {}
    if search:
        query["search_text"] = {"$regex": search.lower()}
    if category != "all":
        query["category"] = category
    if audience != "all":
        query["audience"] = audience
    if division != "all":
        query["$or"] = [{"division_targets": []}, {"division_targets": division}]
    page = normalize_page(page)
    limit = normalize_limit(limit, default=12, max_limit=100)
    total = await deps.db.standards_library.count_documents(query)
    items = (
        await deps.db.standards_library.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response(items, page, limit, total)


@router.post("/standards", status_code=201)
async def create_standard_item(payload: StandardItemRequest, user: dict = Depends(require_roles("management", "owner"))):
    document = {
        "id": make_id("std"),
        "title": payload.title,
        "category": payload.category,
        "audience": payload.audience,
        "division_targets": payload.division_targets,
        "checklist": payload.checklist,
        "notes": payload.notes,
        "owner_notes": payload.owner_notes,
        "shoutout": payload.shoutout,
        "image_url": payload.image_url,
        "training_enabled": payload.training_enabled,
        "question_type": payload.question_type,
        "question_prompt": payload.question_prompt,
        "choice_options": payload.choice_options,
        "correct_answer": payload.correct_answer,
        "is_active": payload.is_active,
        "search_text": " ".join([
            payload.title.lower(),
            payload.category.lower(),
            payload.notes.lower(),
            " ".join(item.lower() for item in payload.division_targets),
        ]),
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    response_document = {**document}
    await deps.db.standards_library.insert_one(document)
    return response_document


@router.patch("/standards/{standard_id}")
async def update_standard_item(
    standard_id: str,
    payload: StandardItemUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    current = await deps.db.standards_library.find_one({"id": standard_id}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Standard item not found")
    patch_values = payload.model_dump(exclude_none=True)
    merged = {**current, **patch_values}
    update = {
        **patch_values,
        "search_text": " ".join([
            merged["title"].lower(),
            merged["category"].lower(),
            merged.get("notes", "").lower(),
            " ".join(item.lower() for item in merged.get("division_targets", [])),
        ]),
        "updated_at": now_iso(),
        "updated_by": user["id"],
    }
    await deps.db.standards_library.update_one({"id": standard_id}, {"$set": update})
    standard = await deps.db.standards_library.find_one({"id": standard_id}, {"_id": 0})
    return standard



DEFAULT_CATEGORIES = [
    "Bed Edging", "Mulching", "Spring Cleanup", "Fall Cleanup", "Property Maintenance",
    "Pruning", "Weeding", "Softscape", "Hardscape", "Tree/Plant Install",
    "Tree/Plant Removal", "Drainage/Trenching", "Lighting", "Stump Grinding",
    "Fert & Chem Treatment", "Air Spade", "Dormant Pruning", "Deer Fencing",
    "Snow Removal", "Plowing", "Salting", "Damage Prevention", "Safety",
    "Tool/Equipment Care", "Client Communication", "Site Prep", "Irrigation",
]


@router.get("/standard-categories")
async def get_standard_categories(user: dict = Depends(require_roles("management", "owner"))):
    db_categories = await deps.db.standards_library.distinct("category")
    merged = sorted(set(DEFAULT_CATEGORIES + [c for c in db_categories if c]))
    return {"categories": merged}


@router.delete("/standards/{standard_id}")
async def delete_standard_item(
    standard_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    existing = await deps.db.standards_library.find_one({"id": standard_id}, {"_id": 0, "id": 1})
    if not existing:
        raise HTTPException(status_code=404, detail="Standard item not found")
    await deps.db.standards_library.delete_one({"id": standard_id})
    return {"deleted": True, "id": standard_id}

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry,
    normalize_page, normalize_limit, build_paginated_response,
    get_crew_link_projection, present_crew_link,
)
from shared.models import CrewAccessCreate, CrewAccessUpdate, CrewLinkStatusUpdateRequest

router = APIRouter()


@router.get("/crew-access-links")
async def get_crew_access_links(
    user: dict = Depends(require_roles("management", "owner")),
    status: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    query: dict[str, Any] = {}
    if status == "active":
        query["enabled"] = True
    elif status == "inactive":
        query["enabled"] = False
    page = normalize_page(page)
    limit = normalize_limit(limit, default=10, max_limit=50)
    total = await deps.db.crew_access_links.count_documents(query)
    crew_links = (
        await deps.db.crew_access_links.find(query, get_crew_link_projection())
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return build_paginated_response([present_crew_link(link) for link in crew_links], page, limit, total)


@router.post("/crew-access-links")
async def create_crew_access_link(payload: CrewAccessCreate, user: dict = Depends(require_roles("management", "owner"))):
    crew_link = {
        "id": make_id("crew"),
        "code": uuid.uuid4().hex[:8],
        "crew_member_id": make_id("crewid").upper(),
        "label": payload.label,
        "leader_name": payload.leader_name,
        "truck_number": payload.truck_number,
        "division": payload.division,
        "assignment": payload.assignment,
        "enabled": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], "Crew QR link created")],
    }
    await deps.db.crew_access_links.insert_one({**crew_link})
    return present_crew_link(crew_link)


@router.patch("/crew-access-links/{crew_link_id}/status")
async def update_crew_access_link_status(
    crew_link_id: str,
    payload: CrewLinkStatusUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    await deps.db.crew_access_links.update_one(
        {"id": crew_link_id},
        {
            "$set": {"enabled": payload.enabled, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("status_update", user["id"], f"enabled={payload.enabled}")},
        },
    )
    crew_link = await deps.db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    if not crew_link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    return present_crew_link(crew_link)


@router.patch("/crew-access-links/{crew_link_id}")
async def update_crew_access_link(
    crew_link_id: str,
    payload: CrewAccessUpdate,
    user: dict = Depends(require_roles("management", "owner")),
):
    # Get the old link to detect division changes
    old_link = await deps.db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    if not old_link:
        raise HTTPException(status_code=404, detail="Crew link not found")

    await deps.db.crew_access_links.update_one(
        {"id": crew_link_id},
        {
            "$set": {
                "label": payload.label,
                "leader_name": payload.leader_name,
                "truck_number": payload.truck_number,
                "division": payload.division,
                "assignment": payload.assignment,
                "updated_at": now_iso(),
            },
            "$push": {"audit_history": audit_entry("updated", user["id"], "Crew QR metadata updated")},
        },
    )

    # Cascade division change to all crew members under this link
    if old_link.get("division") != payload.division:
        await deps.db.crew_members.update_many(
            {"parent_access_code": old_link["code"], "active": True},
            {
                "$set": {
                    "division": payload.division,
                    "updated_at": now_iso(),
                },
                "$push": {"audit_history": audit_entry(
                    "division_switch", user["id"],
                    f"Division changed from '{old_link.get('division', '')}' to '{payload.division}' via crew QR update",
                )},
            },
        )

    crew_link = await deps.db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    return present_crew_link(crew_link)



@router.post("/crew-access-links/{crew_link_id}/archive")
async def archive_crew_access_link(
    crew_link_id: str,
    user: dict = Depends(require_roles("management", "owner")),
):
    link = await deps.db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    await deps.db.crew_access_links.update_one(
        {"id": crew_link_id},
        {
            "$set": {"enabled": False, "archived": True, "archived_at": now_iso(), "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("archived", user["id"], "Crew QR archived")},
        },
    )
    return {"archived": True, "id": crew_link_id}


@router.delete("/crew-access-links/{crew_link_id}")
async def delete_crew_access_link(
    crew_link_id: str,
    user: dict = Depends(require_roles("owner")),
):
    link = await deps.db.crew_access_links.find_one({"id": crew_link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Crew link not found")
    await deps.db.crew_access_links.delete_one({"id": crew_link_id})
    return {"deleted": True, "id": crew_link_id}

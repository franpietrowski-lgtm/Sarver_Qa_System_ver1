from fastapi import APIRouter, Depends, HTTPException

import shared.deps as deps
from shared.deps import (
    require_roles, make_id, now_iso, audit_entry, get_password_hash,
)
from shared.models import UserCreateRequest, UserStatusUpdateRequest

router = APIRouter()


@router.get("/users")
async def get_users(user: dict = Depends(require_roles("management", "owner"))):
    users = await deps.db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(200)
    return users


@router.post("/users")
async def create_user(payload: UserCreateRequest, user: dict = Depends(require_roles("management", "owner"))):
    existing = await deps.db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    record = {
        "id": make_id("user"),
        "name": payload.name,
        "email": payload.email.lower(),
        "role": payload.role,
        "title": payload.title,
        "password_hash": get_password_hash(payload.password),
        "is_active": payload.is_active,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "audit_history": [audit_entry("created", user["id"], f"Staff account created for {payload.title}")],
    }
    await deps.db.users.insert_one({**record})
    record.pop("password_hash", None)
    return record


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdateRequest,
    user: dict = Depends(require_roles("management", "owner")),
):
    await deps.db.users.update_one(
        {"id": user_id},
        {
            "$set": {"is_active": payload.is_active, "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("status_update", user["id"], f"active={payload.is_active}")},
        },
    )
    updated_user = await deps.db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

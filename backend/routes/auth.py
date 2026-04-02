from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import shared.deps as deps
from shared.deps import (
    get_current_user, verify_password, create_access_token,
    get_password_hash, now_iso, audit_entry,
)
from shared.models import LoginRequest

router = APIRouter()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/auth/login")
async def login(payload: LoginRequest):
    user = await deps.db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_access_token(user["id"], user["role"])
    await deps.db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {"last_login_at": now_iso(), "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("login", user["id"], "Successful login")},
        },
    )
    user.pop("password_hash", None)
    return {"token": token, "user": user}


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    full_user = await deps.db.users.find_one({"id": user["id"]}, {"_id": 0})
    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(payload.current_password, full_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    await deps.db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {"password_hash": get_password_hash(payload.new_password), "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("password_change", user["id"], "Password changed by user")},
        },
    )
    return {"message": "Password updated successfully"}


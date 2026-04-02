from typing import Any

from fastapi import APIRouter, Depends, Query

import shared.deps as deps
from shared.deps import require_roles, now_iso, audit_entry

router = APIRouter()


@router.get("/notifications")
async def get_notifications(
    user: dict = Depends(require_roles("management", "owner")),
    status: str = Query("all"),
):
    targets = [{"target_role": user["role"]}, {"target_user_id": user["id"]}]
    if user.get("title"):
        targets.append({"target_titles": user["title"]})
    query: dict[str, Any] = {"$or": targets}
    if status != "all":
        query["status"] = status
    notifications = await deps.db.notifications.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    unread_count = len([item for item in notifications if item.get("status") == "unread"])
    return {"items": notifications, "unread_count": unread_count}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(require_roles("management", "owner"))):
    targets = [{"target_role": user["role"]}, {"target_user_id": user["id"]}]
    if user.get("title"):
        targets.append({"target_titles": user["title"]})
    await deps.db.notifications.update_one(
        {"id": notification_id, "$or": targets},
        {
            "$set": {"status": "read", "updated_at": now_iso()},
            "$push": {"audit_history": audit_entry("read", user["id"], "Notification opened")},
        },
    )
    return {"ok": True}

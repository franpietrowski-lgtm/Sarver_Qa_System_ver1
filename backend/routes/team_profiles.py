from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

import shared.deps as deps
from shared.deps import require_roles, now_iso, utc_now, upload_bytes_to_storage, storage_is_configured, get_storage_bucket

router = APIRouter()


class ProfileUpdate(BaseModel):
    age: int | None = None
    avatar_url: str | None = None


def _build_profile(source_type: str, source_id: str, name: str, role: str, division: str, extras: dict | None = None):
    profile = {
        "profile_id": f"{source_type}_{source_id}",
        "source_type": source_type,
        "source_id": source_id,
        "name": name,
        "role": role,
        "division": division,
        "age": None,
        "avatar_url": "",
    }
    if extras:
        profile["age"] = extras.get("age")
        profile["avatar_url"] = extras.get("avatar_url", "")
    return profile


@router.get("/team/profiles")
async def get_all_profiles(user: dict = Depends(require_roles("management", "owner"))):
    extras_map = {}
    extras_cursor = deps.db.team_profile_extras.find({}, {"_id": 0})
    async for ex in extras_cursor:
        key = f"{ex['source_type']}_{ex['source_id']}"
        extras_map[key] = ex

    profiles = []

    # Staff users
    users_cursor = deps.db.users.find({"active": {"$ne": False}}, {"_id": 0})
    async for u in users_cursor:
        if u.get("name", "").startswith("TEST"):
            continue
        ext = extras_map.get(f"user_{u['id']}")
        p = _build_profile("user", u["id"], u.get("name", ""), u.get("title", u.get("role", "")), "", ext)
        p["email"] = u.get("email", "")
        p["title"] = u.get("title", "")
        p["auth_role"] = u.get("role", "")
        profiles.append(p)

    # Crew leaders (from crew_access_links)
    crews_cursor = deps.db.crew_access_links.find({"enabled": True}, {"_id": 0})
    async for c in crews_cursor:
        if c.get("label", "").startswith("TEST"):
            continue
        ext = extras_map.get(f"crew_{c['code']}")
        display_name = c.get("leader_name") or c.get("label", "")
        p = _build_profile("crew", c["code"], display_name, "Crew Leader", c.get("division", ""), ext)
        p["truck_number"] = c.get("truck_number", "")
        p["crew_code"] = c["code"]
        p["crew_label"] = c.get("label", "")
        profiles.append(p)

    # Crew members
    members_cursor = deps.db.crew_members.find({"active": True}, {"_id": 0})
    async for m in members_cursor:
        if m.get("name", "").startswith("TEST"):
            continue
        ext = extras_map.get(f"member_{m['code']}")
        p = _build_profile("member", m["code"], m.get("name", ""), "Crew Member", m.get("division", ""), ext)
        p["parent_access_code"] = m.get("parent_access_code", "")
        p["parent_crew_label"] = m.get("parent_crew_label", "")
        p["member_code"] = m["code"]
        profiles.append(p)

    return {"profiles": profiles, "total": len(profiles)}


@router.get("/team/profiles/{profile_id}")
async def get_profile_detail(profile_id: str, user: dict = Depends(require_roles("management", "owner"))):
    parts = profile_id.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    source_type, source_id = parts

    ext = await deps.db.team_profile_extras.find_one(
        {"source_type": source_type, "source_id": source_id}, {"_id": 0}
    )
    profile = None

    if source_type == "user":
        u = await deps.db.users.find_one({"id": source_id}, {"_id": 0})
        if u:
            profile = _build_profile("user", u["id"], u.get("name", ""), u.get("title", ""), "", ext)
            profile["email"] = u.get("email", "")
            profile["title"] = u.get("title", "")
            profile["auth_role"] = u.get("role", "")
    elif source_type == "crew":
        c = await deps.db.crew_access_links.find_one({"code": source_id}, {"_id": 0})
        if c:
            profile = _build_profile("crew", c["code"], c.get("label", ""), "Crew Leader", c.get("division", ""), ext)
            profile["truck_number"] = c.get("truck_number", "")
    elif source_type == "member":
        m = await deps.db.crew_members.find_one({"code": source_id}, {"_id": 0})
        if m:
            profile = _build_profile("member", m["code"], m.get("name", ""), "Crew Member", m.get("division", ""), ext)
            profile["parent_crew_label"] = m.get("parent_crew_label", "")

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Attach review stats
    review_query = {}
    if source_type == "user":
        review_query = {"reviewer_id": source_id}
    elif source_type == "crew":
        review_query = {"access_code": source_id}
    elif source_type == "member":
        review_query = {"member_code": source_id}

    review_count = await deps.db.management_reviews.count_documents(review_query)
    submission_count = 0
    if source_type in ("crew", "member"):
        sub_q = {"access_code": source_id} if source_type == "crew" else {"member_code": source_id}
        submission_count = await deps.db.submissions.count_documents(sub_q)

    training_sessions = await deps.db.training_sessions.find(
        {"access_code": source_id} if source_type == "crew" else {"status": {"$exists": False}},
        {"_id": 0, "status": 1, "score_percent": 1},
    ).to_list(50) if source_type in ("crew", "member") else []
    completed_training = sum(1 for t in training_sessions if t.get("status") == "completed")

    profile["stats"] = {
        "review_count": review_count,
        "submission_count": submission_count,
        "training_total": len(training_sessions),
        "training_completed": completed_training,
    }
    return profile


@router.patch("/team/profiles/{profile_id}")
async def update_profile(profile_id: str, payload: ProfileUpdate, user: dict = Depends(require_roles("management", "owner"))):
    parts = profile_id.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    source_type, source_id = parts
    update_data = {}
    if payload.age is not None:
        update_data["age"] = payload.age
    if payload.avatar_url is not None:
        update_data["avatar_url"] = payload.avatar_url
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["source_type"] = source_type
    update_data["source_id"] = source_id
    update_data["updated_at"] = now_iso()
    await deps.db.team_profile_extras.update_one(
        {"source_type": source_type, "source_id": source_id},
        {"$set": update_data},
        upsert=True,
    )
    return {"updated": True, "profile_id": profile_id}


@router.get("/team/structure")
async def get_team_structure(user: dict = Depends(require_roles("management", "owner"))):
    extras_map = {}
    async for ex in deps.db.team_profile_extras.find({}, {"_id": 0}):
        extras_map[f"{ex['source_type']}_{ex['source_id']}"] = ex

    teams = []
    crews = await deps.db.crew_access_links.find({"enabled": True}, {"_id": 0}).to_list(100)
    for c in crews:
        if c.get("label", "").startswith("TEST"):
            continue
        ext = extras_map.get(f"crew_{c['code']}")
        display_name = c.get("leader_name") or c.get("label", "")
        lead = _build_profile("crew", c["code"], display_name, "Crew Leader", c.get("division", ""), ext)
        lead["truck_number"] = c.get("truck_number", "")
        lead["crew_label"] = c.get("label", "")

        members = []
        member_docs = await deps.db.crew_members.find(
            {"parent_access_code": c["code"], "active": True}, {"_id": 0}
        ).to_list(50)
        for m in member_docs:
            if m.get("name", "").startswith("TEST"):
                continue
            m_ext = extras_map.get(f"member_{m['code']}")
            mp = _build_profile("member", m["code"], m.get("name", ""), "Crew Member", m.get("division", ""), m_ext)
            members.append(mp)

        teams.append({"lead": lead, "members": members, "division": c.get("division", ""), "crew_label": c.get("label", "")})
    return {"teams": teams}


@router.get("/team/hierarchy")
async def get_division_hierarchy(user: dict = Depends(require_roles("management", "owner"))):
    extras_map = {}
    async for ex in deps.db.team_profile_extras.find({}, {"_id": 0}):
        extras_map[f"{ex['source_type']}_{ex['source_id']}"] = ex

    def user_profile(u):
        ext = extras_map.get(f"user_{u['id']}")
        p = _build_profile("user", u["id"], u.get("name", ""), u.get("title", ""), u.get("division", ""), ext)
        p["title"] = u.get("title", "")
        p["auth_role"] = u.get("role", "")
        return p

    all_users = await deps.db.users.find({"active": {"$ne": False}}, {"_id": 0}).to_list(200)
    real_users = [u for u in all_users if not u.get("name", "").startswith("TEST")]

    owners = [user_profile(u) for u in real_users if u.get("role") == "owner"]
    gms = [user_profile(u) for u in real_users if u.get("title") == "GM"]
    account_managers = [user_profile(u) for u in real_users if u.get("title") == "Account Manager"]
    production_managers = [user_profile(u) for u in real_users if u.get("title") == "Production Manager"]
    supervisors = [user_profile(u) for u in real_users if u.get("title") == "Supervisor"]

    # Group crews by division
    crews = await deps.db.crew_access_links.find({"enabled": True}, {"_id": 0}).to_list(100)
    division_map = {}
    for c in crews:
        if c.get("label", "").startswith("TEST"):
            continue
        div = c.get("division", "Other")
        if div not in division_map:
            division_map[div] = []
        ext = extras_map.get(f"crew_{c['code']}")
        display_name = c.get("leader_name") or c.get("label", "")
        lead = _build_profile("crew", c["code"], display_name, "Crew Leader", div, ext)
        lead["truck_number"] = c.get("truck_number", "")
        lead["crew_label"] = c.get("label", "")
        members = []
        member_docs = await deps.db.crew_members.find(
            {"parent_access_code": c["code"], "active": True}, {"_id": 0}
        ).to_list(50)
        for m in member_docs:
            if m.get("name", "").startswith("TEST"):
                continue
            m_ext = extras_map.get(f"member_{m['code']}")
            mp = _build_profile("member", m["code"], m.get("name", ""), "Crew Member", m.get("division", ""), m_ext)
            members.append(mp)
        division_map[div].append({"lead": lead, "members": members})

    divisions = []
    for div_name, teams in sorted(division_map.items()):
        divisions.append({"name": div_name, "teams": teams})

    return {
        "owners": owners,
        "general_managers": gms,
        "account_managers": account_managers,
        "production_managers": production_managers,
        "supervisors": supervisors,
        "divisions": divisions,
    }


@router.post("/team/profiles/{profile_id}/avatar")
async def upload_avatar(
    profile_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("management", "owner")),
):
    if not storage_is_configured():
        raise HTTPException(status_code=503, detail="Storage not configured")
    parts = profile_id.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    source_type, source_id = parts
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    path = f"avatars/{profile_id}.{ext}"
    ct = file.content_type or f"image/{ext}"
    await upload_bytes_to_storage(path, content, ct)
    import os
    bucket = get_storage_bucket()
    base_url = os.environ.get("SUPABASE_URL", "")
    avatar_url = f"{base_url}/storage/v1/object/public/{bucket}/{path}"
    await deps.db.team_profile_extras.update_one(
        {"source_type": source_type, "source_id": source_id},
        {"$set": {"avatar_url": avatar_url, "source_type": source_type, "source_id": source_id, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"avatar_url": avatar_url, "profile_id": profile_id}



@router.get("/team/profiles/{profile_id}/stats")
async def get_profile_timeline_stats(
    profile_id: str,
    months: int = Query(3, ge=1, le=24),
    user: dict = Depends(require_roles("management", "owner")),
):
    parts = profile_id.split("_", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid profile ID")
    source_type, source_id = parts
    from datetime import timedelta
    cutoff = (utc_now() - timedelta(days=months * 30)).isoformat()

    review_query = {"created_at": {"$gte": cutoff}}
    sub_query = {"created_at": {"$gte": cutoff}}
    if source_type == "user":
        review_query["reviewer_id"] = source_id
    elif source_type == "crew":
        review_query["access_code"] = source_id
        sub_query["access_code"] = source_id
    elif source_type == "member":
        review_query["member_code"] = source_id
        sub_query["member_code"] = source_id

    review_count = await deps.db.management_reviews.count_documents(review_query)
    submission_count = 0
    avg_score = 0
    if source_type in ("crew", "member"):
        submission_count = await deps.db.submissions.count_documents(sub_query)
    reviews = await deps.db.management_reviews.find(
        review_query, {"_id": 0, "overall_score": 1, "category_scores": 1}
    ).to_list(500)
    if reviews:
        scores = [r.get("overall_score", 0) for r in reviews if r.get("overall_score")]
        avg_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0

    training_query = {"created_at": {"$gte": cutoff}}
    if source_type == "crew":
        training_query["access_code"] = source_id
    elif source_type == "member":
        training_query["member_code"] = source_id
    training_sessions = await deps.db.training_sessions.find(
        training_query, {"_id": 0, "status": 1, "score_percent": 1}
    ).to_list(100) if source_type in ("crew", "member") else []
    training_completed = sum(1 for t in training_sessions if t.get("status") == "completed")
    training_avg = 0
    if training_sessions:
        t_scores = [t.get("score_percent", 0) for t in training_sessions if t.get("score_percent")]
        training_avg = round(sum(t_scores) / max(len(t_scores), 1), 1) if t_scores else 0

    return {
        "months": months,
        "review_count": review_count,
        "submission_count": submission_count,
        "avg_review_score": avg_score,
        "training_total": len(training_sessions),
        "training_completed": training_completed,
        "training_avg_score": training_avg,
    }

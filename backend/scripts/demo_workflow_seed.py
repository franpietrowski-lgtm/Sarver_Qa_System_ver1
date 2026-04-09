"""
Demo Workflow Seed: End-to-end role-based data insertion.
Simulates a real day of work from job creation to grading.

Workflow:
  1. Account Manager (Scott K) creates a job
  2. Production Manager (Tim A) — job assigned to TR-05 (Maintenance Alpha)
  3. Crew Leader (Marcus Thompson) submits 3 photos
  4. Crew Member (Carlos Gutierrez) submits 3 photos (overlapping with leader)
  5. Crew Leader files an emergency damage report (later in day)
  6. 7 admin staff submit rapid reviews / management reviews
     - Excluded: Owner (Adam S), GM (Tyler C), Brad S, Megan M, Daniel T
"""
import asyncio
import os
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from supabase import create_client

# ── Config ──────────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "sarver_landscape")
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET = os.environ["STORAGE_BUCKET_SUBMISSIONS"]

# ── Image URLs (user-provided field photos) ─────────────────────────────
IMAGE_URLS = [
    ("20260402_124535.jpg", "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/ydmvm442_20260402_124535.jpg"),
    ("20260402_124322.jpg", "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/itk00a7z_20260402_124322.jpg"),
    ("20260402_105547.jpg", "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/zte1aobt_20260402_105547.jpg"),
    ("20260401_102938.jpg", "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/ceniqyxa_20260401_102938.jpg"),
    ("20260402_124335.jpg", "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/8bgx7wfl_20260402_124335.jpg"),
]

# ── Helpers ──────────────────────────────────────────────────────────────
def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ago(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

def audit(action: str, actor: str, note: str) -> dict:
    return {"timestamp": now_iso(), "action": action, "actor_id": actor, "note": note}

def build_storage_path(sub_id: str, folder: str, filename: str) -> str:
    return f"sarver-landscape/submissions/{sub_id}/{folder}/{filename}"

def build_file_entry(sub_id: str, filename: str, original: str, seq: int, size: int) -> dict:
    rel = f"/api/submissions/files/{sub_id}/{filename}"
    storage_path = build_storage_path(sub_id, "captures", filename)
    return {
        "id": make_id("file"), "filename": filename, "original_name": original,
        "mime_type": "image/jpeg", "sequence": seq, "size_bytes": size,
        "bucket": BUCKET, "storage_path": storage_path,
        "relative_api_path": rel, "media_url": rel,
        "source_type": "supabase",
    }

def build_issue_file_entry(sub_id: str, filename: str, original: str, seq: int, size: int) -> dict:
    rel = f"/api/submissions/files/{sub_id}/{filename}"
    storage_path = build_storage_path(sub_id, "issues", filename)
    return {
        "id": make_id("issuefile"), "filename": filename, "original_name": original,
        "mime_type": "image/jpeg", "sequence": seq, "size_bytes": size,
        "bucket": BUCKET, "storage_path": storage_path,
        "relative_api_path": rel, "media_url": rel,
        "source_type": "supabase",
    }


async def download_image(client: httpx.AsyncClient, url: str) -> bytes:
    resp = await client.get(url, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def upload_to_supabase(supabase, path: str, content: bytes):
    supabase.storage.from_(BUCKET).upload(path, content, {"content-type": "image/jpeg", "upsert": "true"})


# ── Known IDs (from existing DB) ────────────────────────────────────────
USERS = {
    "owner_adam":  {"id": "user_9aab3ea656ed", "name": "Adam S",    "role": "owner",      "title": "Owner"},
    "gm_tyler":    {"id": "user_7d3f3d0ab8d4", "name": "Tyler C",   "role": "management", "title": "GM"},
    "pm_tim":      {"id": "user_c3d870e64f6b", "name": "Tim A",     "role": "management", "title": "Production Manager"},
    "pm_scott_w":  {"id": "user_a1077d9038c4", "name": "Scott W",   "role": "management", "title": "Production Manager"},
    "pm_zach":     {"id": "user_68aba95a11cd", "name": "Zach O",    "role": "management", "title": "Production Manager"},
    "pm_brad":     {"id": "user_29cdbb587ecf", "name": "Brad S",    "role": "management", "title": "Production Manager"},
    "am_scott_k":  {"id": "user_e65431dfc6f7", "name": "Scott K",   "role": "management", "title": "Account Manager"},
    "am_megan":    {"id": "user_d6cbafb48621", "name": "Megan M",   "role": "management", "title": "Account Manager"},
    "am_daniel":   {"id": "user_bb0b6e199d05", "name": "Daniel T",  "role": "management", "title": "Account Manager"},
    "sup_fran":    {"id": "user_1434bc414ddd", "name": "Fran P",    "role": "management", "title": "Supervisor"},
    "sup_craig":   {"id": "user_5b05c2f02a17", "name": "Craig S",   "role": "management", "title": "Supervisor"},
    "sup_johnny":  {"id": "user_506e4a05b27f", "name": "Johnny H",  "role": "management", "title": "Supervisor"},
}

CREW_MAINT_ALPHA = {
    "code": "be1da0c6", "label": "Maintenance Alpha",
    "leader": "Marcus Thompson", "truck": "TR-05", "division": "Maintenance",
}

# Carlos Gutierrez is a crew member under Maintenance Alpha
CREW_MEMBER_CARLOS = {"name": "Carlos Gutierrez"}


# ── Main Seed ────────────────────────────────────────────────────────────
async def main():
    print("=== DEMO WORKFLOW SEED ===\n")

    client_mongo = AsyncIOMotorClient(MONGO_URL)
    db = client_mongo[DB_NAME]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # -- Step 0: Download all 5 images --
    print("[0] Downloading 5 field photos...")
    image_data = {}
    async with httpx.AsyncClient(timeout=30) as http:
        for fname, url in IMAGE_URLS:
            image_data[fname] = await download_image(http, url)
            print(f"    Downloaded {fname} ({len(image_data[fname]):,} bytes)")

    # -- Step 1: Account Manager (Scott K) creates a job --
    print("\n[1] Account Manager (Scott K) creating job...")
    job_id_str = "LMN-6001"
    job = {
        "id": make_id("job"),
        "job_id": job_id_str,
        "job_name": "Longvue HOA - 291 Mailbox Bed Edging",
        "property_name": "Longvue HOA",
        "address": "291 Longvue Dr, Wexford PA 15090",
        "service_type": "bed edging",
        "scheduled_date": "2026-04-09",
        "division": "Maintenance",
        "truck_number": "TR-05",
        "route": "LV-WEST",
        "latitude": "40.6237",
        "longitude": "-80.0603",
        "source": "account_manager",
        "search_text": f"{job_id_str} longvue hoa 291 mailbox bed edging 291 longvue dr wexford pa 15090".lower(),
        "created_at": ago(8),
        "updated_at": ago(8),
        "audit_history": [
            audit("created", USERS["am_scott_k"]["id"], "Job created by Account Manager Scott K"),
        ],
    }
    await db.jobs.update_one({"job_id": job_id_str}, {"$set": job}, upsert=True)
    print(f"    Job {job_id_str}: {job['job_name']} (truck {job['truck_number']})")

    # -- Step 2: PM Tim A review -- The job is assigned to TR-05 which is Maint Alpha's truck.
    # Tim A conceptually reviews the daily crew assignment (no explicit API call needed;
    # the job is on TR-05 so Maintenance Alpha crew sees it when they open their portal).
    print("\n[2] PM Tim A (Maintenance) — job TR-05 assigned to Maintenance Alpha. Crew can see it.")

    # -- Step 3: Crew Leader (Marcus Thompson) submits 3 photos --
    print("\n[3] Crew Leader (Marcus Thompson) submitting 3 photos...")
    sub_leader_id = make_id("sub")
    leader_photos = []
    photo_mapping_leader = [
        (1, "20260402_124535.jpg"),  # Mailbox 291 wide angle
        (2, "20260402_124322.jpg"),  # Mailbox 285 detail
        (3, "20260402_105547.jpg"),  # Close-up edging along border
    ]
    for seq, orig_name in photo_mapping_leader:
        fname = f"{seq:02d}_{uuid.uuid4().hex[:6]}.jpg"
        content = image_data[orig_name]
        storage_path = build_storage_path(sub_leader_id, "captures", fname)
        upload_to_supabase(supabase, storage_path, content)
        leader_photos.append(build_file_entry(sub_leader_id, fname, orig_name, seq, len(content)))
        print(f"    Uploaded {orig_name} -> {storage_path}")

    leader_submission = {
        "id": sub_leader_id,
        "submission_code": sub_leader_id.upper(),
        "access_code": CREW_MAINT_ALPHA["code"],
        "crew_label": CREW_MAINT_ALPHA["label"],
        "job_key": job_id_str,
        "job_id": job_id_str,
        "job_name_input": job["job_name"],
        "matched_job_id": job["id"],
        "match_status": "confirmed",
        "match_confidence": 1.0,
        "truck_number": CREW_MAINT_ALPHA["truck"],
        "division": CREW_MAINT_ALPHA["division"],
        "service_type": "bed edging",
        "task_type": "bed edging",
        "status": "Ready for Review",
        "note": "Mailbox beds 291 and 285 — fresh edging and mulch applied. Clean lines achieved.",
        "area_tag": "Front entrance / mailbox beds",
        "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
        "gps": {"lat": 40.6237, "lng": -80.0603, "accuracy": 0.8},
        "gps_low_confidence": False,
        "work_date": "2026-04-09",
        "captured_at": ago(5),
        "required_photo_count": 3,
        "photo_count": 3,
        "photo_files": leader_photos,
        "local_folder_path": f"/tmp/submissions/{sub_leader_id}",
        "device_metadata": {"user_agent": "Android/CrewApp/MarcusThompson"},
        "storage_status": "stored",
        "member_code": None,
        "is_emergency": False,
        "created_at": ago(5),
        "updated_at": ago(5),
        "audit_history": [
            audit("submitted", CREW_MAINT_ALPHA["code"], "Crew Leader Marcus Thompson submitted bed edging photos"),
            audit("status_change", CREW_MAINT_ALPHA["code"], "Lifecycle moved to Ready for Review"),
        ],
    }
    await db.submissions.update_one({"id": sub_leader_id}, {"$set": leader_submission}, upsert=True)
    print(f"    Submission {sub_leader_id}: {leader_submission['note'][:60]}...")

    # -- Step 4: Crew Member (Carlos Gutierrez) submits 3 photos --
    print("\n[4] Crew Member (Carlos Gutierrez) submitting 3 photos...")
    # Carlos uses member_code. Let's check if he has one; if not, we'll use access_code only.
    carlos_member = await db.crew_members.find_one(
        {"parent_access_code": CREW_MAINT_ALPHA["code"], "name": {"$regex": "Carlos", "$options": "i"}},
        {"_id": 0}
    )
    carlos_member_code = carlos_member["code"] if carlos_member else None

    sub_member_id = make_id("sub")
    member_photos = []
    photo_mapping_member = [
        (1, "20260402_124335.jpg"),  # Rural bed/mulch work by road
        (2, "20260401_102938.jpg"),  # Dump truck near shrubs — arrival photo
        (3, "20260402_105547.jpg"),  # Close-up edging (same as leader photo 3 but different angle of bed)
    ]
    for seq, orig_name in photo_mapping_member:
        fname = f"{seq:02d}_{uuid.uuid4().hex[:6]}.jpg"
        content = image_data[orig_name]
        storage_path = build_storage_path(sub_member_id, "captures", fname)
        upload_to_supabase(supabase, storage_path, content)
        member_photos.append(build_file_entry(sub_member_id, fname, orig_name, seq, len(content)))
        print(f"    Uploaded {orig_name} -> {storage_path}")

    member_submission = {
        "id": sub_member_id,
        "submission_code": sub_member_id.upper(),
        "access_code": CREW_MAINT_ALPHA["code"],
        "crew_label": CREW_MAINT_ALPHA["label"],
        "job_key": job_id_str,
        "job_id": job_id_str,
        "job_name_input": job["job_name"],
        "matched_job_id": job["id"],
        "match_status": "confirmed",
        "match_confidence": 0.95,
        "truck_number": CREW_MAINT_ALPHA["truck"],
        "division": CREW_MAINT_ALPHA["division"],
        "service_type": "bed edging",
        "task_type": "bed edging",
        "status": "Ready for Review",
        "note": "Arrival + edging detail from entrance bed area. Mulch depth 3 inches applied.",
        "area_tag": "Entrance island / driveway beds",
        "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
        "gps": {"lat": 40.6238, "lng": -80.0601, "accuracy": 1.2},
        "gps_low_confidence": False,
        "work_date": "2026-04-09",
        "captured_at": ago(4),
        "required_photo_count": 3,
        "photo_count": 3,
        "photo_files": member_photos,
        "local_folder_path": f"/tmp/submissions/{sub_member_id}",
        "device_metadata": {"user_agent": "Android/CrewApp/CarlosGutierrez"},
        "storage_status": "stored",
        "member_code": carlos_member_code,
        "is_emergency": False,
        "created_at": ago(4),
        "updated_at": ago(4),
        "audit_history": [
            audit("submitted", CREW_MAINT_ALPHA["code"], "Crew Member Carlos Gutierrez submitted bed edging photos"),
            audit("status_change", CREW_MAINT_ALPHA["code"], "Lifecycle moved to Ready for Review"),
        ],
    }
    await db.submissions.update_one({"id": sub_member_id}, {"$set": member_submission}, upsert=True)
    print(f"    Submission {sub_member_id}: {member_submission['note'][:60]}...")

    # -- Step 5: Emergency damage report from Crew Leader --
    print("\n[5] Crew Leader (Marcus Thompson) filing emergency damage report...")
    sub_emergency_id = make_id("sub")
    emergency_issue_photo_fname = f"issue_01_{uuid.uuid4().hex[:6]}.jpg"
    damage_content = image_data["20260401_102938.jpg"]  # Dump truck near shrubs = potential plant damage
    issue_storage = build_storage_path(sub_emergency_id, "issues", emergency_issue_photo_fname)
    upload_to_supabase(supabase, issue_storage, damage_content)
    issue_file = build_issue_file_entry(sub_emergency_id, emergency_issue_photo_fname, "20260401_102938.jpg", 1, len(damage_content))

    emergency_submission = {
        "id": sub_emergency_id,
        "submission_code": sub_emergency_id.upper(),
        "access_code": CREW_MAINT_ALPHA["code"],
        "crew_label": CREW_MAINT_ALPHA["label"],
        "job_key": job_id_str,
        "job_id": job_id_str,
        "job_name_input": job["job_name"],
        "matched_job_id": job["id"],
        "match_status": "confirmed",
        "match_confidence": 1.0,
        "truck_number": CREW_MAINT_ALPHA["truck"],
        "division": CREW_MAINT_ALPHA["division"],
        "service_type": "bed edging",
        "task_type": "bed edging",
        "status": "Ready for Review",
        "note": "DAMAGE: Dump truck wheel crushed two Mugo Pine shrubs on approach. Client may notice. PM notified verbally.",
        "area_tag": "Front driveway plantings",
        "field_report": {
            "type": "Incident / Accident",
            "notes": "During mulch delivery, the dump truck backed into the planting bed near the driveway. Two Mugo Pine shrubs and one boxwood sustained crush damage from the rear wheel. Truck driver misjudged clearance. Photos attached. Client not yet notified — requesting PM guidance.",
            "photo_files": [issue_file],
            "reported": True,
        },
        "gps": {"lat": 40.6236, "lng": -80.0604, "accuracy": 1.0},
        "gps_low_confidence": False,
        "work_date": "2026-04-09",
        "captured_at": ago(2),
        "required_photo_count": 3,
        "photo_count": 0,
        "photo_files": [],
        "local_folder_path": f"/tmp/submissions/{sub_emergency_id}",
        "device_metadata": {"user_agent": "Android/CrewApp/MarcusThompson"},
        "storage_status": "stored",
        "member_code": None,
        "is_emergency": True,
        "incident_acknowledged": False,
        "created_at": ago(2),
        "updated_at": ago(2),
        "audit_history": [
            audit("submitted", CREW_MAINT_ALPHA["code"], "EMERGENCY: Crew Leader Marcus Thompson filed damage/incident report"),
            audit("status_change", CREW_MAINT_ALPHA["code"], "Lifecycle moved to Ready for Review"),
        ],
    }
    await db.submissions.update_one({"id": sub_emergency_id}, {"$set": emergency_submission}, upsert=True)
    print(f"    Emergency {sub_emergency_id}: Dump truck plant damage")

    # Create emergency notification
    await db.notifications.insert_one({
        "id": make_id("notif"),
        "title": "EMERGENCY: Incident/Accident Report Filed",
        "message": f"Maintenance Alpha reported 'Incident / Accident' on {job['job_name']}.",
        "audience": "all",
        "target_titles": ["Supervisor", "Production Manager", "Account Manager", "GM", "Owner"],
        "related_submission_id": sub_emergency_id,
        "related_job_id": job_id_str,
        "notification_type": "emergency_incident",
        "status": "unread",
        "created_at": ago(2),
        "updated_at": ago(2),
    })

    # -- Step 6: Grading --
    # Get the rubric for bed edging
    rubric = await db.rubric_definitions.find_one(
        {"service_type": "bed edging", "is_active": True}, {"_id": 0}
    )
    rubric_id = rubric["id"]
    rubric_version = rubric["version"]
    category_keys = [c["key"] for c in rubric["categories"]]

    print(f"\n[6] Grading with rubric: {rubric['title']} (categories: {category_keys})")

    # -- 6a: Rapid Reviews (5 reviewers on leader submission) --
    rapid_reviewers = [
        ("pm_tim",      "standard",  "Solid edging on both mailbox beds. Consistent depth, clean mulch application.", 8200),
        ("pm_scott_w",  "standard",  "Acceptable work. Minor gap near the 285 mailbox base could use touch-up.", 6500),
        ("sup_fran",    "exemplary", "Excellent curb appeal. Sharp lines, uniform mulch depth, very clean finish.", 12000),
        ("sup_craig",   "standard",  "Good overall. Turf containment is clean. Mulch could be slightly thicker by the lamp post.", 7100),
        ("sup_johnny",  "standard",  "Standard quality bed edging. Nothing out of line.", 5500),
    ]

    rating_multipliers = {"fail": 0.0, "concern": 0.35, "standard": 0.72, "exemplary": 1.0}

    for key, rating, comment, duration_ms in rapid_reviewers:
        user = USERS[key]
        total_weight = sum(c["weight"] for c in rubric["categories"])
        normalized_pct = round(total_weight * rating_multipliers[rating] * 100, 1)
        review = {
            "id": make_id("rapid"),
            "submission_id": sub_leader_id,
            "reviewer_id": user["id"],
            "reviewer_role": user["role"],
            "reviewer_title": user["title"],
            "rubric_id": rubric_id,
            "rubric_version": rubric_version,
            "service_type": "bed edging",
            "overall_rating": rating,
            "rubric_sum_percent": normalized_pct,
            "multiplier": rating_multipliers[rating],
            "comment": comment,
            "issue_tag": "",
            "annotation_count": 0,
            "entry_mode": "desktop",
            "swipe_duration_ms": duration_ms,
            "flagged_fast": duration_ms < 4000 and rating in {"standard", "exemplary"},
            "flagged_concern": rating == "concern",
            "needs_manual_rescore": rating == "concern",
            "created_at": ago(3),
            "updated_at": ago(3),
            "audit_history": [audit("rapid_reviewed", user["id"], f"Rapid review marked {rating}")],
        }
        await db.rapid_reviews.update_one(
            {"submission_id": sub_leader_id, "reviewer_id": user["id"]},
            {"$set": review}, upsert=True,
        )
        print(f"    Rapid Review by {user['name']:12s} ({user['title']:20s}): {rating:10s} ({normalized_pct}%)")

    # -- 6b: Management Review on member submission (Scott K, Account Manager) --
    am_scores = {"continuity": 4.2, "depth_consistency": 4.0, "turf_containment": 3.8, "cleanliness": 4.5, "visual_finish": 4.0}
    total_score = 0.0
    for cat in rubric["categories"]:
        raw = min(float(am_scores.get(cat["key"], 0)), cat["max_score"])
        total_score += (raw / cat["max_score"]) * cat["weight"]
    total_score = round(total_score * 100, 1)

    mgmt_review = {
        "id": make_id("mgr"),
        "submission_id": sub_member_id,
        "reviewer_id": USERS["am_scott_k"]["id"],
        "rubric_id": rubric_id,
        "rubric_version": rubric_version,
        "service_type": "bed edging",
        "category_scores": am_scores,
        "total_score": total_score,
        "comments": "Carlos did well on cleanliness. Depth consistency slightly uneven near the driveway entrance but acceptable overall. Turf edges need a bit more definition.",
        "disposition": "approved",
        "flagged_issues": [],
        "created_at": ago(3),
        "updated_at": ago(3),
        "audit_history": [audit("created", USERS["am_scott_k"]["id"], "Management review submitted by Scott K")],
    }
    await db.management_reviews.update_one(
        {"submission_id": sub_member_id}, {"$set": mgmt_review}, upsert=True,
    )
    await db.submissions.update_one(
        {"id": sub_member_id},
        {"$set": {"status": "Management Reviewed", "updated_at": ago(3)}},
    )
    print(f"    Management Review by Scott K (AM): score={total_score}% disposition=approved")

    # -- 6c: Rapid Review on member submission (PM Zach O) --
    zach_review = {
        "id": make_id("rapid"),
        "submission_id": sub_member_id,
        "reviewer_id": USERS["pm_zach"]["id"],
        "reviewer_role": USERS["pm_zach"]["role"],
        "reviewer_title": USERS["pm_zach"]["title"],
        "rubric_id": rubric_id,
        "rubric_version": rubric_version,
        "service_type": "bed edging",
        "overall_rating": "standard",
        "rubric_sum_percent": round(sum(c["weight"] for c in rubric["categories"]) * rating_multipliers["standard"] * 100, 1),
        "multiplier": rating_multipliers["standard"],
        "comment": "Crew member did solid work. Entrance island bed looks clean. Arrival truck photo is a nice touch for documentation.",
        "issue_tag": "",
        "annotation_count": 0,
        "entry_mode": "desktop",
        "swipe_duration_ms": 9200,
        "flagged_fast": False,
        "flagged_concern": False,
        "needs_manual_rescore": False,
        "created_at": ago(3),
        "updated_at": ago(3),
        "audit_history": [audit("rapid_reviewed", USERS["pm_zach"]["id"], "Rapid review marked standard")],
    }
    await db.rapid_reviews.update_one(
        {"submission_id": sub_member_id, "reviewer_id": USERS["pm_zach"]["id"]},
        {"$set": zach_review}, upsert=True,
    )
    print(f"    Rapid Review by Zach O   (PM, Install):    standard")

    # -- Summary --
    print("\n" + "=" * 60)
    print("DEMO WORKFLOW SEED COMPLETE")
    print("=" * 60)
    print(f"""
Job Created:     {job_id_str} — {job['job_name']}
                 Division: Maintenance | Truck: TR-05 | Route: LV-WEST
                 Created by: Scott K (Account Manager)

Submissions:
  1. {sub_leader_id}  — Crew Leader (Marcus Thompson)
     3 photos: Mailbox beds 291 & 285, edging detail
     Status: Ready for Review
     Rapid Reviews: Tim A, Scott W, Fran P, Craig S, Johnny H

  2. {sub_member_id}  — Crew Member (Carlos Gutierrez)
     3 photos: Entrance island, dump truck arrival, edging detail
     Status: Management Reviewed
     Mgmt Review: Scott K (82.6%) | Rapid Review: Zach O

  3. {sub_emergency_id}  — EMERGENCY (Marcus Thompson)
     Dump truck crushed Mugo Pine shrubs near driveway
     Issue photo: 1 | Is Emergency: True
     Status: Ready for Review (unacknowledged)

Grading Summary:
  Reviewed:   Tim A (PM), Scott W (PM), Zach O (PM), Scott K (AM),
              Fran P (Sup), Craig S (Sup), Johnny H (Sup) — 7 total
  Excluded:   Adam S (Owner), Tyler C (GM),
              Brad S (PM-Tree), Megan M (AM), Daniel T (AM) — 5 total
""")

    client_mongo.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

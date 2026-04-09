"""Data cleanup: delete photoless submissions (except alpha demo), create real submissions with user photos, setup Tim as crew leader."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

def utc_now(): return datetime.now(timezone.utc)
def now_iso(): return utc_now().isoformat()
def make_id(prefix=""): return f"{prefix}_{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]
def audit_entry(action, actor, note=""): return {"action": action, "actor": actor, "note": note, "timestamp": now_iso()}

UPLOADED_PHOTOS = [
    {"url": "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/fkg5ndff_1b0b2567-2c8d-4206-ab41-22c2837044f0.jpg", "desc": "Drainage gravel bed install overview"},
    {"url": "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/f04cdk4c_39190497-465a-43db-ab09-a94e57e97d19.jpg", "desc": "Drainage grate and gravel detail"},
    {"url": "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/j2yllqi8_eedd9c19-7761-44fa-a78f-25de342f9aa7.jpg", "desc": "Soil prep and drainage contour"},
    {"url": "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/bfr4oyfs_567026c8-39d6-4125-8863-9013e7c9ba3b.jpg", "desc": "Worker soil grading at property edge"},
    {"url": "https://customer-assets.emergentagent.com/job_4db37b4f-6a1b-43ef-8a21-2618e4329894/artifacts/ze0fi2v2_94508f1d-873e-467d-832e-7804f3c617ff.jpg", "desc": "Worker edge trimming near house"},
]


async def main():
    # 1. Delete submissions without real photos (except alpha demo crew bb01032c for onboarding)
    result = await db.submissions.delete_many({
        "storage_status": {"$ne": "stored"},
        "access_code": {"$nin": ["bb01032c"]},
        "$or": [
            {"photo_files": {"$exists": False}},
            {"photo_files": []},
            {"storage_status": "seed_remote"},
        ],
    })
    print(f"Deleted {result.deleted_count} photoless submissions (kept alpha demo)")

    # 2. Deactivate demo crew members that aren't Fran-related, Tim, or alpha demo
    keep_codes = set()
    # Alex Rivera is on Install Alpha (bb01032c) - keep for onboarding demo
    alex = await db.crew_members.find_one({"name": "Alex Rivera"}, {"_id": 0})
    if alex: keep_codes.add(alex["code"])
    # Tim Connely - keep
    tim = await db.crew_members.find_one({"name": "Tim Connely"}, {"_id": 0})
    if tim: keep_codes.add(tim["code"])

    # Deactivate others
    if keep_codes:
        deactivated = await db.crew_members.update_many(
            {"code": {"$nin": list(keep_codes)}},
            {"$set": {"active": False, "updated_at": now_iso()}}
        )
        print(f"Deactivated {deactivated.modified_count} demo crew members (kept Alex, Tim)")

    # 3. Set up Tim Connely as a proper Maintenance crew leader
    tim_link = await db.crew_access_links.find_one({"code": "6ef4489a"}, {"_id": 0})
    if tim_link:
        await db.crew_access_links.update_one(
            {"code": "6ef4489a"},
            {"$set": {
                "label": "Tim's Crew", "leader_name": "Tim Connely",
                "truck_number": "TR-20", "division": "Maintenance",
                "assignment": "General Maintenance",
                "updated_at": now_iso(),
            }}
        )
        print("Updated Tim's crew link (6ef4489a) to Maintenance crew leader")

    # Also give Tim a crew_member entry linked to his own crew link so he can access member screen
    existing_tim_member = await db.crew_members.find_one({"name": "Tim Connely"}, {"_id": 0})
    if existing_tim_member:
        await db.crew_members.update_one(
            {"code": existing_tim_member["code"]},
            {"$set": {
                "parent_access_code": "6ef4489a",
                "parent_crew_label": "Tim's Crew",
                "parent_truck_number": "TR-20",
                "division": "Maintenance",
                "active": True,
                "updated_at": now_iso(),
            }}
        )
        print(f"Updated Tim's member entry (code: {existing_tim_member['code']}) to link to Tim's Crew")

    # 4. Set up Fran's crew link properly
    fran_link = await db.crew_access_links.find_one({"code": "5ca6684e"}, {"_id": 0})
    if fran_link:
        await db.crew_access_links.update_one(
            {"code": "5ca6684e"},
            {"$set": {
                "label": "Fran's Crew", "leader_name": "Fran P",
                "truck_number": "TR-15", "division": "Install",
                "assignment": "Drainage & Trenching",
                "updated_at": now_iso(),
            }}
        )
        print("Updated Fran's crew link (5ca6684e)")

    # 5. Create the main drainage job at Longvue HOA Pittsburgh
    main_job_id = make_id("job")
    main_job = {
        "id": main_job_id, "job_id": "LMN-5001",
        "job_name": "Longvue HOA Drainage & Grading",
        "property_name": "Longvue HOA", "address": "Longvue Dr, Pittsburgh PA 15218",
        "service_type": "drainage/trenching", "scheduled_date": utc_now().isoformat(),
        "division": "Install", "truck_number": "TR-15", "route": "East Route",
        "source": "admin", "search_text": "lmn-5001 longvue hoa drainage grading pittsburgh",
        "created_at": now_iso(), "updated_at": now_iso(),
        "audit_history": [audit_entry("created", "system", "Real job for photo testing")],
    }
    await db.jobs.insert_one(main_job)
    print(f"Created main job: {main_job['job_name']} ({main_job_id})")

    # Also create related sub-jobs for different task aspects visible in photos
    sub_jobs = [
        {"id": make_id("job"), "job_id": "LMN-5002", "job_name": "Longvue HOA Ground Prep & Seeding", "property_name": "Longvue HOA", "address": "Longvue Dr, Pittsburgh PA 15218", "service_type": "softscape", "division": "Install"},
        {"id": make_id("job"), "job_id": "LMN-5003", "job_name": "Longvue HOA Bed Edging Restore", "property_name": "Longvue HOA", "address": "Longvue Dr, Pittsburgh PA 15218", "service_type": "bed edging", "division": "Maintenance"},
    ]
    for sj in sub_jobs:
        sj.update({
            "scheduled_date": utc_now().isoformat(), "truck_number": "TR-15", "route": "East Route",
            "source": "admin", "search_text": f"{sj['job_id'].lower()} longvue hoa {sj['service_type']}",
            "created_at": now_iso(), "updated_at": now_iso(),
            "audit_history": [audit_entry("created", "system", "Sub-task job for photo testing")],
        })
    await db.jobs.insert_many(sub_jobs)
    print(f"Created {len(sub_jobs)} sub-task jobs")

    # 6. Create the main submission with all 5 photos under Fran's crew
    main_sub_id = make_id("sub")
    photo_files = []
    for i, photo in enumerate(UPLOADED_PHOTOS):
        photo_files.append({
            "id": make_id("file"), "filename": f"longvue-drainage-{i+1}.jpg",
            "mime_type": "image/jpeg", "sequence": i + 1,
            "source_type": "uploaded", "media_url": photo["url"],
            "description": photo["desc"],
        })

    main_submission = {
        "id": main_sub_id, "submission_code": main_sub_id.upper(),
        "access_code": "5ca6684e", "crew_label": "Fran's Crew",
        "job_id": "LMN-5001", "job_name_input": "Longvue HOA Drainage & Grading",
        "matched_job_id": main_job_id, "match_status": "confirmed", "match_confidence": 1.0,
        "truck_number": "TR-15", "division": "Install",
        "service_type": "drainage/trenching", "task_type": "drainage/trenching",
        "status": "Ready for Review",
        "note": "Drainage gravel bed installation complete. Grate placed. Soil grading in progress. Awaiting seeding.",
        "area_tag": "Rear yard - slope",
        "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
        "gps": {"lat": 40.4317, "lng": -79.9036, "accuracy": 4},
        "work_date": utc_now().strftime("%Y-%m-%d"),
        "captured_at": now_iso(),
        "photo_count": 5, "required_photo_count": 3,
        "photo_files": photo_files,
        "storage_status": "stored",
        "is_emergency": False,
        "created_at": now_iso(), "updated_at": now_iso(),
        "audit_history": [audit_entry("submitted", "crew", "Fran's Crew real photo submission")],
    }
    await db.submissions.insert_one(main_submission)
    print(f"Created main submission with 5 real photos ({main_sub_id})")

    # 7. Create additional submissions for sub-jobs (referencing subsets of photos)
    # Ground prep/seeding submission (photos 3,4)
    sub1_id = make_id("sub")
    await db.submissions.insert_one({
        "id": sub1_id, "submission_code": sub1_id.upper(),
        "access_code": "5ca6684e", "crew_label": "Fran's Crew",
        "job_id": "LMN-5002", "job_name_input": "Longvue HOA Ground Prep & Seeding",
        "matched_job_id": sub_jobs[0]["id"], "match_status": "confirmed", "match_confidence": 0.95,
        "truck_number": "TR-15", "division": "Install",
        "service_type": "softscape", "task_type": "softscape",
        "status": "Ready for Review",
        "note": "Soil prep and rough grading complete. Ready for topsoil and seed.",
        "area_tag": "Rear yard - slope",
        "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
        "gps": {"lat": 40.4318, "lng": -79.9035, "accuracy": 3},
        "work_date": utc_now().strftime("%Y-%m-%d"),
        "captured_at": (utc_now() - timedelta(hours=2)).isoformat(),
        "photo_count": 3, "required_photo_count": 3,
        "photo_files": [
            {"id": make_id("file"), "filename": "longvue-ground-prep-1.jpg", "mime_type": "image/jpeg", "sequence": 1, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[2]["url"]},
            {"id": make_id("file"), "filename": "longvue-ground-prep-2.jpg", "mime_type": "image/jpeg", "sequence": 2, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[3]["url"]},
            {"id": make_id("file"), "filename": "longvue-ground-prep-3.jpg", "mime_type": "image/jpeg", "sequence": 3, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[4]["url"]},
        ],
        "storage_status": "stored", "is_emergency": False,
        "created_at": (utc_now() - timedelta(hours=2)).isoformat(), "updated_at": now_iso(),
        "audit_history": [audit_entry("submitted", "crew", "Ground prep submission")],
    })
    print(f"Created ground prep submission ({sub1_id})")

    # Bed edging restore submission (photos 4,5)
    sub2_id = make_id("sub")
    await db.submissions.insert_one({
        "id": sub2_id, "submission_code": sub2_id.upper(),
        "access_code": "5ca6684e", "crew_label": "Fran's Crew",
        "job_id": "LMN-5003", "job_name_input": "Longvue HOA Bed Edging Restore",
        "matched_job_id": sub_jobs[1]["id"], "match_status": "confirmed", "match_confidence": 0.90,
        "truck_number": "TR-15", "division": "Maintenance",
        "service_type": "bed edging", "task_type": "bed edging",
        "status": "Ready for Review",
        "note": "Restored bed lines along property edge. Some debris visible near walkway.",
        "area_tag": "Property edge - south side",
        "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
        "gps": {"lat": 40.4316, "lng": -79.9037, "accuracy": 5},
        "work_date": utc_now().strftime("%Y-%m-%d"),
        "captured_at": (utc_now() - timedelta(hours=1)).isoformat(),
        "photo_count": 3, "required_photo_count": 3,
        "photo_files": [
            {"id": make_id("file"), "filename": "longvue-edging-1.jpg", "mime_type": "image/jpeg", "sequence": 1, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[3]["url"]},
            {"id": make_id("file"), "filename": "longvue-edging-2.jpg", "mime_type": "image/jpeg", "sequence": 2, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[4]["url"]},
            {"id": make_id("file"), "filename": "longvue-edging-3.jpg", "mime_type": "image/jpeg", "sequence": 3, "source_type": "uploaded", "media_url": UPLOADED_PHOTOS[0]["url"]},
        ],
        "storage_status": "stored", "is_emergency": False,
        "created_at": (utc_now() - timedelta(hours=1)).isoformat(), "updated_at": now_iso(),
        "audit_history": [audit_entry("submitted", "crew", "Bed edging submission")],
    })
    print(f"Created bed edging submission ({sub2_id})")

    # 8. Add "no image / improper image capture" as a hard fail condition to ALL rubric definitions
    rubric_update = await db.rubric_definitions.update_many(
        {},
        {"$addToSet": {"hard_fail_conditions": {"$each": ["no_image_captured", "improper_image_quality"]}}}
    )
    print(f"Added no_image/improper_image hard-fail to {rubric_update.modified_count} rubric definitions")

    # Summary
    total_subs = await db.submissions.count_documents({})
    active_members = await db.crew_members.count_documents({"active": True})
    print(f"\nFinal state: {total_subs} submissions, {active_members} active crew members")

asyncio.run(main())

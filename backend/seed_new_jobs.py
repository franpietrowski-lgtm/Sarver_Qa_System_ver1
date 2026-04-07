"""One-time script to seed 12 new demo jobs + submissions."""
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


def utc_now():
    return datetime.now(timezone.utc)


def now_iso():
    return utc_now().isoformat()


def make_id(prefix=""):
    return f"{prefix}_{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:8]


def audit_entry(action, actor, note=""):
    return {"action": action, "actor": actor, "note": note, "timestamp": now_iso()}


async def main():
    existing = await db.jobs.count_documents({"job_id": {"$regex": "^LMN-42"}})
    if existing > 0:
        print(f"Already have {existing} LMN-42xx jobs, skipping")
        return

    new_jobs = [
        {"id": make_id("job"), "job_id": "LMN-4201", "job_name": "Birch Hill Spring Cleanup", "property_name": "Birch Hill Village", "address": "302 Birch Hill Rd", "service_type": "spring cleanup", "scheduled_date": (utc_now() - timedelta(days=10)).isoformat(), "division": "Maintenance", "truck_number": "TR-12", "route": "East Route", "source": "seed", "search_text": "lmn-4201 birch hill spring cleanup birch hill village", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4202", "job_name": "Brighton Commons Mulching", "property_name": "Brighton Commons", "address": "1488 Brighton Blvd", "service_type": "mulching", "scheduled_date": (utc_now() - timedelta(days=20)).isoformat(), "division": "Maintenance", "truck_number": "TR-18", "route": "Central Route", "source": "seed", "search_text": "lmn-4202 brighton commons mulching", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4203", "job_name": "Cedar Court Bed Edging", "property_name": "Cedar Court Condos", "address": "77 Cedar Court Dr", "service_type": "bed edging", "scheduled_date": (utc_now() - timedelta(days=30)).isoformat(), "division": "Maintenance", "truck_number": "TR-24", "route": "North Route", "source": "seed", "search_text": "lmn-4203 cedar court bed edging condos", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4204", "job_name": "Cedar Point Pruning", "property_name": "Cedar Point Business Park", "address": "2200 Cedar Point Way", "service_type": "pruning", "scheduled_date": (utc_now() - timedelta(days=40)).isoformat(), "division": "Maintenance", "truck_number": "TR-12", "route": "East Route", "source": "seed", "search_text": "lmn-4204 cedar point pruning business park", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4205", "job_name": "Greenfield Plaza Weeding", "property_name": "Greenfield Plaza", "address": "405 Greenfield Ave", "service_type": "weeding", "scheduled_date": (utc_now() - timedelta(days=50)).isoformat(), "division": "Maintenance", "truck_number": "TR-18", "route": "South Route", "source": "seed", "search_text": "lmn-4205 greenfield plaza weeding", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4206", "job_name": "Glen Meadow Property Maintenance", "property_name": "Glen Meadow Estates", "address": "119 Glen Meadow Ln", "service_type": "property maintenance", "scheduled_date": (utc_now() - timedelta(days=60)).isoformat(), "division": "Maintenance", "truck_number": "TR-24", "route": "Central Route", "source": "seed", "search_text": "lmn-4206 glen meadow property maintenance estates", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4207", "job_name": "Highland Ridge Spring Cleanup", "property_name": "Highland Ridge Homes", "address": "650 Highland Ridge Ct", "service_type": "spring cleanup", "scheduled_date": (utc_now() - timedelta(days=70)).isoformat(), "division": "Maintenance", "truck_number": "TR-12", "route": "North Route", "source": "seed", "search_text": "lmn-4207 highland ridge spring cleanup homes", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4208", "job_name": "Hilltop Gardens Mulching", "property_name": "Hilltop Gardens", "address": "88 Hilltop Terrace", "service_type": "mulching", "scheduled_date": (utc_now() - timedelta(days=80)).isoformat(), "division": "Maintenance", "truck_number": "TR-18", "route": "East Route", "source": "seed", "search_text": "lmn-4208 hilltop gardens mulching terrace", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4209", "job_name": "Lakeshore Commons Bed Edging", "property_name": "Lakeshore Commons", "address": "3310 Lakeshore Dr", "service_type": "bed edging", "scheduled_date": (utc_now() - timedelta(days=90)).isoformat(), "division": "Maintenance", "truck_number": "TR-24", "route": "South Route", "source": "seed", "search_text": "lmn-4209 lakeshore commons bed edging", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4210", "job_name": "Lakewood Estates Pruning", "property_name": "Lakewood Estates", "address": "270 Lakewood Blvd", "service_type": "pruning", "scheduled_date": (utc_now() - timedelta(days=100)).isoformat(), "division": "Maintenance", "truck_number": "TR-12", "route": "Central Route", "source": "seed", "search_text": "lmn-4210 lakewood estates pruning boulevard", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4211", "job_name": "Oakridge Valley Weeding", "property_name": "Oakridge Valley HOA", "address": "515 Oakridge Valley Rd", "service_type": "weeding", "scheduled_date": (utc_now() - timedelta(days=110)).isoformat(), "division": "Maintenance", "truck_number": "TR-18", "route": "North Route", "source": "seed", "search_text": "lmn-4211 oakridge valley weeding hoa", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
        {"id": make_id("job"), "job_id": "LMN-4212", "job_name": "Oak Summit Property Maintenance", "property_name": "Oak Summit Center", "address": "900 Oak Summit Pkwy", "service_type": "property maintenance", "scheduled_date": (utc_now() - timedelta(days=120)).isoformat(), "division": "Maintenance", "truck_number": "TR-24", "route": "East Route", "source": "seed", "search_text": "lmn-4212 oak summit property maintenance center", "created_at": now_iso(), "updated_at": now_iso(), "audit_history": [audit_entry("seeded", "system", "Demo job")]},
    ]
    result = await db.jobs.insert_many(new_jobs)
    print(f"Inserted {len(result.inserted_ids)} new demo jobs")

    crew_links = await db.crew_access_links.find({}, {"_id": 0}).to_list(10)
    if not crew_links:
        print("No crew links, skipping submissions")
        return

    photo_urls = [
        "https://images.pexels.com/photos/6728925/pexels-photo-6728925.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "https://images.unsplash.com/photo-1696663118264-55a63c75409b?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "https://images.unsplash.com/photo-1605117882932-f9e32b03fea9?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
    ]
    notes = ["Minor issues found", "Good quality work", "Needs improvement near walkway", "Clean finish on beds", "Slight debris left", "Excellent coverage"]
    areas = ["Front entry", "Parking lot", "North beds", "Main walkway", "Rear fence", "Side lot"]
    statuses = ["Ready for Review", "Management Reviewed", "Management Reviewed", "Export Ready"]

    subs = []
    for i, job in enumerate(new_jobs):
        crew = crew_links[i % len(crew_links)]
        days_ago = (i + 1) * 10
        ts = (utc_now() - timedelta(days=days_ago)).isoformat()
        sub_id = make_id("sub")
        subs.append({
            "id": sub_id, "submission_code": sub_id.upper(),
            "access_code": crew["code"], "crew_label": crew["label"],
            "job_id": job["job_id"], "job_name_input": job["job_name"],
            "matched_job_id": job["id"], "match_status": "confirmed", "match_confidence": 0.92,
            "truck_number": job["truck_number"], "division": job["division"],
            "service_type": job["service_type"], "task_type": job["service_type"],
            "status": statuses[i % len(statuses)],
            "note": notes[i % len(notes)], "area_tag": areas[i % len(areas)],
            "field_report": {"type": "", "notes": "", "photo_files": [], "reported": False},
            "gps": {"lat": 43.631 + (i * 0.002), "lng": -79.412 + (i * 0.001), "accuracy": 5},
            "work_date": (utc_now() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "captured_at": ts,
            "photo_count": 3, "required_photo_count": 3,
            "photo_files": [{"id": make_id("file"), "filename": f"seed-{sub_id[-6:]}-1.jpg", "mime_type": "image/jpeg", "sequence": 1, "source_type": "remote", "media_url": photo_urls[i % len(photo_urls)]}],
            "storage_status": "seed_remote",
            "is_emergency": False,
            "created_at": ts, "updated_at": ts,
            "audit_history": [audit_entry("seeded", "system", "Demo submission for new job")],
        })
    result = await db.submissions.insert_many(subs)
    print(f"Inserted {len(result.inserted_ids)} submissions for new jobs")


asyncio.run(main())

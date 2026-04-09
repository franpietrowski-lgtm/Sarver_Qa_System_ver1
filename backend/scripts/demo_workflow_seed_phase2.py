"""
Demo Workflow Seed — Phase 2: Distribute grading across unreviewed submissions.
The job, submissions, and first rapid review (Tim A on leader sub) were created in Phase 1.
This script adds the remaining rapid reviews + management review.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "sarver_landscape")

def make_id(prefix):
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def ago(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

def audit(action, actor, note):
    return {"timestamp": now_iso(), "action": action, "actor_id": actor, "note": note}

USERS = {
    "pm_scott_w":  {"id": "user_a1077d9038c4", "name": "Scott W",   "role": "management", "title": "Production Manager"},
    "pm_zach":     {"id": "user_68aba95a11cd", "name": "Zach O",    "role": "management", "title": "Production Manager"},
    "am_scott_k":  {"id": "user_e65431dfc6f7", "name": "Scott K",   "role": "management", "title": "Account Manager"},
    "sup_fran":    {"id": "user_1434bc414ddd", "name": "Fran P",    "role": "management", "title": "Supervisor"},
    "sup_craig":   {"id": "user_5b05c2f02a17", "name": "Craig S",   "role": "management", "title": "Supervisor"},
    "sup_johnny":  {"id": "user_506e4a05b27f", "name": "Johnny H",  "role": "management", "title": "Supervisor"},
}

RATING_MULTIPLIERS = {"fail": 0.0, "concern": 0.35, "standard": 0.72, "exemplary": 1.0}


async def main():
    print("=== DEMO WORKFLOW SEED — Phase 2: Grading Distribution ===\n")

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Get all unreviewed submissions (no rapid review yet)
    reviewed_ids = await db.rapid_reviews.distinct("submission_id", {})
    unreviewed = await db.submissions.find(
        {
            "service_type": {"$ne": ""},
            "status": {"$in": ["Ready for Review", "Management Reviewed", "Owner Reviewed", "Export Ready"]},
            "id": {"$nin": reviewed_ids},
        },
        {"_id": 0},
    ).sort("created_at", -1).to_list(20)

    print(f"Found {len(unreviewed)} unreviewed submissions")
    for s in unreviewed:
        print(f"  {s['id']:25s} | {s.get('crew_label','?'):20s} | {s.get('service_type','?')}")

    # Assign reviewers to submissions (one per submission)
    assignments = [
        # (reviewer_key, submission_id, rating, comment, duration_ms)
    ]

    # Map known IDs
    sub_member = "sub_7d5246c4a4a9"   # Carlos Gutierrez member submission
    sub_fran_be = "sub_9a2d6002"      # Fran's Crew bed edging
    sub_fran_dt = "sub_763b4179"      # Fran's Crew drainage/trenching
    sub_fran_ss = "sub_8d9e7217"      # Fran's Crew softscape
    sub_install_pm = "sub_309c7fee"   # Install Alpha property maintenance
    sub_install_wd = "sub_8ff2e50e"   # Install Alpha weeding

    # Build assignment list from what's unreviewed
    potential = [
        ("pm_scott_w",  sub_member,     "standard",  "Acceptable bed edging from crew member. Mulch depth looks even. Arrival photo is good documentation practice.", 7400),
        ("pm_zach",     sub_fran_be,    "standard",  "Fran's crew maintains consistent bed edging quality. No issues.", 6100),
        ("am_scott_k",  sub_fran_dt,    "exemplary", "Excellent drainage/trenching work. Grade is smooth, trench alignment is precise. Textbook execution.", 11500),
        ("sup_fran",    sub_fran_ss,    "standard",  "Softscape installation meets standard. Plants spaced correctly and mulch ring is proper.", 8200),
        ("sup_craig",   sub_install_pm, "concern",   "Property maintenance submission lacks clarity on which specific tasks were completed. Need more detail in crew notes.", 5800),
        ("sup_johnny",  sub_install_wd, "standard",  "Weeding job looks complete. Beds are clean.", 4200),
    ]

    # Filter to only submissions that are actually unreviewed
    unreviewed_ids = {s["id"] for s in unreviewed}
    for key, sub_id, rating, comment, duration in potential:
        if sub_id in unreviewed_ids:
            assignments.append((key, sub_id, rating, comment, duration))

    print(f"\nAssigning {len(assignments)} rapid reviews...")

    for key, sub_id, rating, comment, duration in assignments:
        user = USERS[key]
        # Get rubric for this submission
        submission = await db.submissions.find_one({"id": sub_id}, {"_id": 0, "service_type": 1})
        svc = (submission or {}).get("service_type", "bed edging")
        rubric = await db.rubric_definitions.find_one(
            {"service_type": svc.lower(), "is_active": True}, {"_id": 0}
        )
        if not rubric:
            print(f"  SKIP {sub_id}: No rubric for '{svc}'")
            continue

        total_weight = sum(c["weight"] for c in rubric.get("categories", []))
        normalized_pct = round(total_weight * RATING_MULTIPLIERS[rating] * 100, 1)

        review = {
            "id": make_id("rapid"),
            "submission_id": sub_id,
            "reviewer_id": user["id"],
            "reviewer_role": user["role"],
            "reviewer_title": user["title"],
            "rubric_id": rubric["id"],
            "rubric_version": rubric["version"],
            "service_type": svc,
            "overall_rating": rating,
            "rubric_sum_percent": normalized_pct,
            "multiplier": RATING_MULTIPLIERS[rating],
            "comment": comment,
            "issue_tag": "",
            "annotation_count": 0,
            "entry_mode": "desktop",
            "swipe_duration_ms": duration,
            "flagged_fast": duration < 4000 and rating in {"standard", "exemplary"},
            "flagged_concern": rating == "concern",
            "needs_manual_rescore": rating == "concern",
            "created_at": ago(2),
            "updated_at": ago(2),
            "audit_history": [audit("rapid_reviewed", user["id"], f"Rapid review marked {rating}")],
        }
        await db.rapid_reviews.update_one(
            {"submission_id": sub_id}, {"$set": review}, upsert=True,
        )
        # Update submission audit trail
        await db.submissions.update_one(
            {"id": sub_id},
            {
                "$set": {"updated_at": ago(2)},
                "$push": {"audit_history": audit("rapid_reviewed", user["id"], f"Rapid review marked {rating}")},
            },
        )
        print(f"  {user['name']:12s} ({user['title']:20s}) -> {sub_id} [{svc}] = {rating} ({normalized_pct}%)")

    # Management review for member submission (Scott K)
    rubric_be = await db.rubric_definitions.find_one(
        {"service_type": "bed edging", "is_active": True}, {"_id": 0}
    )
    if rubric_be and sub_member in unreviewed_ids:
        am_scores = {"continuity": 4.2, "depth_consistency": 4.0, "turf_containment": 3.8, "cleanliness": 4.5, "visual_finish": 4.0}
        total_score = 0.0
        for cat in rubric_be["categories"]:
            raw = min(float(am_scores.get(cat["key"], 0)), cat["max_score"])
            total_score += (raw / cat["max_score"]) * cat["weight"]
        total_score = round(total_score * 100, 1)

        mgmt_review = {
            "id": make_id("mgr"),
            "submission_id": sub_member,
            "reviewer_id": USERS["am_scott_k"]["id"],
            "rubric_id": rubric_be["id"],
            "rubric_version": rubric_be["version"],
            "service_type": "bed edging",
            "category_scores": am_scores,
            "total_score": total_score,
            "comments": "Carlos did well on cleanliness. Depth consistency slightly uneven near the driveway entrance but acceptable overall.",
            "disposition": "approved",
            "flagged_issues": [],
            "created_at": ago(2),
            "updated_at": ago(2),
            "audit_history": [audit("created", USERS["am_scott_k"]["id"], "Management review submitted by Scott K")],
        }
        await db.management_reviews.update_one(
            {"submission_id": sub_member}, {"$set": mgmt_review}, upsert=True,
        )
        await db.submissions.update_one(
            {"id": sub_member},
            {"$set": {"status": "Management Reviewed", "updated_at": ago(2)}},
        )
        print(f"\n  Management Review: Scott K -> {sub_member} [bed edging] score={total_score}%")

    print("\n" + "=" * 60)
    print("GRADING DISTRIBUTION COMPLETE")
    print("=" * 60)
    print(f"""
Grading Summary (7 reviewers participated):
  Tim A (PM Maintenance)    -> Leader submission [bed edging]      = standard  (Phase 1)
  Scott W (PM Maintenance)  -> Member submission [bed edging]      = standard
  Zach O (PM Install)       -> Fran bed edging                     = standard
  Scott K (AM)              -> Fran drainage/trenching             = exemplary + Mgmt Review on member sub
  Fran P (Supervisor)       -> Fran softscape                      = standard
  Craig S (Supervisor)      -> Install property maintenance        = concern
  Johnny H (Supervisor)     -> Install weeding                     = standard

Excluded from grading (5):
  Adam S (Owner), Tyler C (GM), Brad S (PM-Tree), Megan M (AM), Daniel T (AM)
""")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

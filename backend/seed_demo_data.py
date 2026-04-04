"""
Seed demo crews, members, submissions, reviews, training sessions, and standard checks.
Creates realistic data for onboarding and dashboard exploration.

Crews:
  1. "Maintenance Alpha" (3-man) → PM: Tim A (Maintenance)
  2. "Maintenance Bravo" (4-man) → PM: Scott W (Maintenance)
  3. "Tree Alpha" (4-man: 3 tree + 1 PHC) → PM: Brad S (Tree)
"""
import asyncio
import os
import uuid
import random
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def make_id(prefix=""):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def past_date(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()

def random_date_between(start_days_ago, end_days_ago):
    d = random.randint(end_days_ago, start_days_ago)
    return past_date(d)

MAINT_TASKS = ["Bed edging", "Spring/Fall Cleanup", "Pruning", "Weeding", "Mulching", "Property Maintenance"]
TREE_TASKS = ["Pruning", "Tree/Plant Install/Removal", "Removal", "Stump Grinding"]
PHC_TASKS = ["Fert and Chem treatments", "Air Spade", "Dormant pruning"]
JOB_NAMES = [
    "123 Oak Street", "456 Elm Ave", "789 Birch Lane", "101 Maple Dr", "55 Walnut Ct",
    "200 Pine Ridge", "312 Cedar Blvd", "88 Ash Way", "401 Spruce St", "77 Willow Path",
    "650 Dogwood Ln", "33 Magnolia Rd", "910 Hickory Ct", "204 Sycamore Ave", "15 Chestnut St",
]
FAIL_NOTES = [
    "Edge line inconsistent in several sections",
    "Missed debris behind fence line",
    "Mulch piled against trunk — volcano noted",
    "PPE: no safety glasses during trim",
    "Cut quality below standard — stubs noted",
]
PASS_NOTES = [
    "Clean work, confident lines throughout",
    "Full property reset looks complete",
    "Good detail on cut quality",
    "Professional finish visible from street",
    "Excellent documentation photos",
]
EXEMPLARY_NOTES = [
    "Textbook execution — use as training example",
    "Outstanding attention to detail",
    "Best submission this quarter",
]

# Crew definitions
CREWS = [
    {
        "label": "Maintenance Alpha",
        "leader_name": "Marcus Thompson",
        "division": "Maintenance",
        "truck_number": "TR-05",
        "assignment": "North Properties",
        "start_date_days_ago": 540,  # ~18 months
        "members": [
            {"name": "Carlos Gutierrez", "start_days_ago": 480},
            {"name": "James Patterson", "start_days_ago": 320},
        ],
    },
    {
        "label": "Maintenance Bravo",
        "leader_name": "Derek Washington",
        "division": "Maintenance",
        "truck_number": "TR-08",
        "assignment": "South Properties",
        "start_date_days_ago": 650,  # ~22 months
        "members": [
            {"name": "Luis Hernandez", "start_days_ago": 600},
            {"name": "Ryan Mitchell", "start_days_ago": 400},
            {"name": "Kevin O'Brien", "start_days_ago": 210},
        ],
    },
    {
        "label": "Tree Alpha",
        "leader_name": "Nathan Cole",
        "division": "Tree",
        "truck_number": "TR-12",
        "assignment": "Citywide Tree Service",
        "start_date_days_ago": 500,
        "members": [
            {"name": "Miguel Santos", "start_days_ago": 450, "specialty": "Tree"},
            {"name": "Tyler Brooks", "start_days_ago": 370, "specialty": "Tree"},
            {"name": "David Park", "start_days_ago": 280, "specialty": "Plant Healthcare"},
        ],
    },
]

# Management reviewer IDs (will be fetched dynamically)
REVIEWER_ROLES = ["management", "owner"]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Get existing reviewer user IDs
    reviewers = []
    async for u in db.users.find({"active": {"$ne": False}, "role": {"$in": REVIEWER_ROLES}}, {"_id": 0, "id": 1, "name": 1, "role": 1}):
        reviewers.append(u)
    print(f"Found {len(reviewers)} reviewers")

    # Get existing standards for training data
    standards = await db.standards_library.find({"training_enabled": True}, {"_id": 0, "id": 1, "title": 1, "question_prompt": 1, "correct_answer": 1, "choice_options": 1, "division_targets": 1}).to_list(50)
    print(f"Found {len(standards)} training-enabled standards")

    created_crews = []

    for crew_def in CREWS:
        # Check if crew already exists
        existing = await db.crew_access_links.find_one({"label": crew_def["label"]}, {"_id": 0})
        if existing:
            print(f"  Crew '{crew_def['label']}' already exists — skipping")
            created_crews.append({"code": existing["code"], "def": crew_def})
            continue

        code = uuid.uuid4().hex[:8]
        crew_link = {
            "id": make_id("crew"),
            "code": code,
            "crew_member_id": make_id("crewid").upper(),
            "label": crew_def["label"],
            "leader_name": crew_def["leader_name"],
            "truck_number": crew_def["truck_number"],
            "division": crew_def["division"],
            "assignment": crew_def["assignment"],
            "enabled": True,
            "archived": False,
            "created_at": past_date(crew_def["start_date_days_ago"]),
            "updated_at": now_iso(),
        }
        await db.crew_access_links.insert_one(crew_link)
        print(f"  Created crew: {crew_def['label']} (code={code})")

        # Create members
        for m in crew_def["members"]:
            m_code = uuid.uuid4().hex[:8]
            member_doc = {
                "id": make_id("member"),
                "code": m_code,
                "parent_access_code": code,
                "name": m["name"],
                "division": m.get("specialty", crew_def["division"]),
                "active": True,
                "created_at": past_date(m["start_days_ago"]),
                "updated_at": now_iso(),
            }
            await db.crew_members.insert_one(member_doc)
            m["code"] = m_code
            print(f"    Member: {m['name']} (code={m_code})")

        created_crews.append({"code": code, "def": crew_def})

    # Now create submissions and reviews for each crew
    print("\n--- Generating submissions, reviews, and training data ---")

    for crew_info in created_crews:
        code = crew_info["code"]
        crew_def = crew_info["def"]
        division = crew_def["division"]
        tasks = MAINT_TASKS if division == "Maintenance" else TREE_TASKS

        # Check if submissions already exist for this crew
        existing_subs = await db.submissions.count_documents({"access_code": code})
        if existing_subs > 3:
            print(f"  Crew {crew_def['label']} already has {existing_subs} submissions — skipping data gen")
            continue

        # Generate 8-15 submissions over the crew's lifetime
        num_submissions = random.randint(8, 15)
        start_days = crew_def["start_date_days_ago"]

        for i in range(num_submissions):
            sub_date = random_date_between(start_days, 5)
            job = random.choice(JOB_NAMES)
            task = random.choice(tasks)

            submission = {
                "id": make_id("sub"),
                "access_code": code,
                "job_name": f"{job} — {task}",
                "division": division,
                "task_type": task,
                "truck_number": crew_def["truck_number"],
                "photos": [],
                "gps_lat": round(40.4 + random.uniform(-0.1, 0.1), 6),
                "gps_lng": round(-79.9 + random.uniform(-0.1, 0.1), 6),
                "notes": f"Completed {task.lower()} for {job}",
                "status": "Management Reviewed",
                "created_at": sub_date,
                "updated_at": sub_date,
            }
            await db.submissions.insert_one(submission)

            # Create management review for ~80% of submissions
            if random.random() < 0.8:
                reviewer = random.choice(reviewers)
                # Score distribution: 60% pass (3.5-4.5), 25% good (4.5-5), 10% exemplary (5), 5% fail (1-3)
                roll = random.random()
                if roll < 0.05:
                    score = round(random.uniform(1.5, 3.0), 1)
                    verdict = "Fail"
                    remark = random.choice(FAIL_NOTES)
                elif roll < 0.65:
                    score = round(random.uniform(3.5, 4.5), 1)
                    verdict = "Pass"
                    remark = random.choice(PASS_NOTES)
                elif roll < 0.90:
                    score = round(random.uniform(4.5, 5.0), 1)
                    verdict = "Pass"
                    remark = random.choice(PASS_NOTES)
                else:
                    score = 5.0
                    verdict = "Exemplary"
                    remark = random.choice(EXEMPLARY_NOTES)

                review = {
                    "id": make_id("rev"),
                    "submission_id": submission["id"],
                    "access_code": code,
                    "reviewer_id": reviewer["id"],
                    "reviewer_name": reviewer.get("name", "Reviewer"),
                    "overall_score": score,
                    "category_scores": {
                        "quality": round(score + random.uniform(-0.5, 0.3), 1),
                        "documentation": round(score + random.uniform(-0.3, 0.5), 1),
                        "safety": round(min(5, score + random.uniform(0, 0.5)), 1),
                    },
                    "verdict": verdict,
                    "remarks": remark,
                    "created_at": sub_date,
                    "updated_at": sub_date,
                }
                await db.management_reviews.insert_one(review)

        print(f"  {crew_def['label']}: {num_submissions} submissions created")

        # Generate training sessions for crew (2-5 per crew)
        div_standards = [s for s in standards if not s.get("division_targets") or division in s.get("division_targets", [])]
        num_training = random.randint(2, 5)
        for _ in range(num_training):
            std = random.choice(div_standards) if div_standards else random.choice(standards)
            passed = random.random() < 0.75
            training = {
                "id": make_id("train"),
                "code": uuid.uuid4().hex[:8],
                "access_code": code,
                "standard_id": std["id"],
                "standard_title": std.get("title", "Unknown"),
                "status": "completed" if passed else "failed",
                "score_percent": random.randint(70, 100) if passed else random.randint(20, 65),
                "answers": [],
                "created_at": random_date_between(start_days, 10),
                "updated_at": now_iso(),
            }
            await db.training_sessions.insert_one(training)

        print(f"  {crew_def['label']}: {num_training} training sessions created")

        # Generate training for individual members too
        member_docs_list = await db.crew_members.find({"parent_access_code": code, "active": True}, {"_id": 0, "code": 1, "name": 1, "division": 1}).to_list(20)
        for m in member_docs_list:
            member_division = m.get("division", division)
            m_standards = [s for s in standards if not s.get("division_targets") or member_division in s.get("division_targets", [])]
            num_m_training = random.randint(1, 3)
            for _ in range(num_m_training):
                std = random.choice(m_standards) if m_standards else random.choice(standards)
                passed = random.random() < 0.7
                t = {
                    "id": make_id("train"),
                    "code": uuid.uuid4().hex[:8],
                    "member_code": m["code"],
                    "access_code": code,
                    "standard_id": std["id"],
                    "standard_title": std.get("title", "Unknown"),
                    "status": "completed" if passed else "failed",
                    "score_percent": random.randint(65, 100) if passed else random.randint(15, 60),
                    "answers": [],
                    "created_at": random_date_between(300, 10),
                    "updated_at": now_iso(),
                }
                await db.training_sessions.insert_one(t)

    # Also create a few rapid reviews
    all_subs = await db.submissions.find({}, {"_id": 0, "id": 1, "access_code": 1, "division": 1}).to_list(50)
    rapid_count = 0
    for sub in random.sample(all_subs, min(10, len(all_subs))):
        existing_rapid = await db.rapid_reviews.find_one({"submission_id": sub["id"]})
        if existing_rapid:
            continue
        reviewer = random.choice(reviewers)
        verdict = random.choice(["pass", "pass", "pass", "pass", "fail", "exemplary"])
        rapid = {
            "id": make_id("rapid"),
            "submission_id": sub["id"],
            "access_code": sub.get("access_code", ""),
            "reviewer_id": reviewer["id"],
            "verdict": verdict,
            "remarks": random.choice(PASS_NOTES) if verdict == "pass" else (random.choice(FAIL_NOTES) if verdict == "fail" else random.choice(EXEMPLARY_NOTES)),
            "created_at": now_iso(),
        }
        await db.rapid_reviews.insert_one(rapid)
        rapid_count += 1
    print(f"  Created {rapid_count} rapid reviews")

    # Summary
    total_crews = await db.crew_access_links.count_documents({"enabled": True})
    total_members = await db.crew_members.count_documents({"active": True})
    total_subs = await db.submissions.count_documents({})
    total_reviews = await db.management_reviews.count_documents({})
    total_training = await db.training_sessions.count_documents({})
    total_rapid = await db.rapid_reviews.count_documents({})

    print(f"\n=== DATA SUMMARY ===")
    print(f"  Crews: {total_crews}")
    print(f"  Members: {total_members}")
    print(f"  Submissions: {total_subs}")
    print(f"  Management Reviews: {total_reviews}")
    print(f"  Training Sessions: {total_training}")
    print(f"  Rapid Reviews: {total_rapid}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())

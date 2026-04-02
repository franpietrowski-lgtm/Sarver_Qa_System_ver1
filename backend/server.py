import logging
import os
import uuid
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

import shared.deps as deps
from shared.deps import (
    make_id, now_iso, audit_entry, get_password_hash, utc_now,
    get_active_rubric, storage_is_configured, get_supabase_client,
    SUBMISSIONS_DIR, DATA_DIR, EXPORTS_DIR,
)

from routes.auth import router as auth_router
from routes.system import router as system_router
from routes.public import router as public_router
from routes.submissions import router as submissions_router
from routes.equipment import router as equipment_router
from routes.jobs import router as jobs_router
from routes.crew_access import router as crew_access_router
from routes.users import router as users_router
from routes.notifications import router as notifications_router
from routes.rubrics import router as rubrics_router
from routes.standards import router as standards_router
from routes.reviews import router as reviews_router
from routes.rapid_reviews import router as rapid_reviews_router
from routes.training import router as training_router
from routes.analytics import router as analytics_router
from routes.exports import router as exports_router
from routes.integrations import router as integrations_router
from routes.reviewer_performance import router as reviewer_performance_router
from routes.coaching import router as coaching_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
deps.db = db

app = FastAPI(title="Field Quality Capture & Review System")
api_router = APIRouter(prefix="/api")


# ── Seed Data Constants ────────────────────────────────────────────────

RUBRIC_LIBRARY = [
    {
        "id": "rubric_bed_edging_v1",
        "service_type": "bed edging",
        "division": "Maintenance",
        "title": "Bed Edging v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 78,
        "hard_fail_conditions": ["property_damage", "unsafe_debris_left_behind"],
        "categories": [
            {"key": "continuity", "label": "Continuity", "weight": 0.22, "max_score": 5},
            {"key": "depth_consistency", "label": "Depth Consistency", "weight": 0.24, "max_score": 5},
            {"key": "turf_containment", "label": "Turf Containment", "weight": 0.18, "max_score": 5},
            {"key": "cleanliness", "label": "Cleanliness", "weight": 0.16, "max_score": 5},
            {"key": "visual_finish", "label": "Visual Finish", "weight": 0.2, "max_score": 5},
        ],
    },
    {
        "id": "rubric_spring_cleanup_v1",
        "service_type": "spring cleanup",
        "division": "Maintenance",
        "title": "Spring Cleanup v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 80,
        "hard_fail_conditions": ["missed_debris_zone", "damaged_bed_material"],
        "categories": [
            {"key": "coverage", "label": "Coverage", "weight": 0.24, "max_score": 5},
            {"key": "cleanliness", "label": "Cleanliness", "weight": 0.24, "max_score": 5},
            {"key": "bed_definition", "label": "Bed Definition", "weight": 0.18, "max_score": 5},
            {"key": "turf_finish", "label": "Turf Finish", "weight": 0.16, "max_score": 5},
            {"key": "curb_appeal", "label": "Curb Appeal", "weight": 0.18, "max_score": 5},
        ],
    },
    {
        "id": "rubric_fall_cleanup_v1",
        "service_type": "fall cleanup",
        "division": "Maintenance",
        "title": "Fall Cleanup v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 81,
        "hard_fail_conditions": ["leaf_buildup_remaining", "blocked_drainage"],
        "categories": [
            {"key": "leaf_removal", "label": "Leaf Removal", "weight": 0.26, "max_score": 5},
            {"key": "detail_finish", "label": "Detail Finish", "weight": 0.2, "max_score": 5},
            {"key": "bed_cleanup", "label": "Bed Cleanup", "weight": 0.18, "max_score": 5},
            {"key": "walkway_clearance", "label": "Walkway Clearance", "weight": 0.18, "max_score": 5},
            {"key": "visual_finish", "label": "Visual Finish", "weight": 0.18, "max_score": 5},
        ],
    },
    {
        "id": "rubric_property_maintenance_v1",
        "service_type": "property maintenance",
        "division": "Maintenance",
        "title": "Property Maintenance v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 80,
        "hard_fail_conditions": ["unsafe_site_left", "major_missed_scope"],
        "categories": [
            {"key": "horticultural_quality", "label": "Horticultural Quality", "weight": 0.34, "max_score": 5},
            {"key": "scope_completeness", "label": "Scope Completeness", "weight": 0.33, "max_score": 5},
            {"key": "site_finish", "label": "Site Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_pruning_v1",
        "service_type": "pruning",
        "division": "Maintenance",
        "title": "Pruning v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 82,
        "hard_fail_conditions": ["plant_damage", "unsafe_cutting_practice"],
        "categories": [
            {"key": "cut_quality", "label": "Cut Quality", "weight": 0.34, "max_score": 5},
            {"key": "shape_intent", "label": "Shape Intent", "weight": 0.33, "max_score": 5},
            {"key": "cleanup_finish", "label": "Cleanup Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_weeding_v1",
        "service_type": "weeding",
        "division": "Maintenance",
        "title": "Weeding v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 80,
        "hard_fail_conditions": ["weed_patch_missed", "ornamental_damage"],
        "categories": [
            {"key": "weed_removal", "label": "Weed Removal", "weight": 0.34, "max_score": 5},
            {"key": "bed_protection", "label": "Bed Protection", "weight": 0.33, "max_score": 5},
            {"key": "final_cleanup", "label": "Final Cleanup", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_mulching_v1",
        "service_type": "mulching",
        "division": "Maintenance",
        "title": "Mulching v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 82,
        "hard_fail_conditions": ["mulch_on_turf", "root_flare_buried"],
        "categories": [
            {"key": "depth_consistency", "label": "Depth Consistency", "weight": 0.34, "max_score": 5},
            {"key": "bed_definition", "label": "Bed Definition", "weight": 0.33, "max_score": 5},
            {"key": "spill_control", "label": "Spill Control", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_softscape_v1",
        "service_type": "softscape",
        "division": "Install",
        "title": "Softscape v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 83,
        "hard_fail_conditions": ["material_damage", "layout_miss"],
        "categories": [
            {"key": "layout_accuracy", "label": "Layout Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "material_condition", "label": "Material Condition", "weight": 0.33, "max_score": 5},
            {"key": "finish_detail", "label": "Finish Detail", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_hardscape_v1",
        "service_type": "hardscape",
        "division": "Install",
        "title": "Hardscape v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 84,
        "hard_fail_conditions": ["trip_hazard", "failed_alignment"],
        "categories": [
            {"key": "alignment_grade", "label": "Alignment / Grade", "weight": 0.34, "max_score": 5},
            {"key": "stability_compaction", "label": "Stability / Compaction", "weight": 0.33, "max_score": 5},
            {"key": "finish_detail", "label": "Finish Detail", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_tree_plant_install_removal_v1",
        "service_type": "tree/plant install/removal",
        "division": "Install",
        "title": "Tree/Plant Install/Removal v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 82,
        "hard_fail_conditions": ["unsafe_lift", "site_damage"],
        "categories": [
            {"key": "safety_control", "label": "Safety / Control", "weight": 0.34, "max_score": 5},
            {"key": "plant_material_handling", "label": "Plant/Material Handling", "weight": 0.33, "max_score": 5},
            {"key": "site_restoration", "label": "Site Restoration", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_drainage_trenching_v1",
        "service_type": "drainage/trenching",
        "division": "Install",
        "title": "Drainage/Trenching v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 82,
        "hard_fail_conditions": ["poor_grade", "unsafe_open_trench"],
        "categories": [
            {"key": "trench_accuracy", "label": "Trench Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "drainage_function", "label": "Drainage Function", "weight": 0.33, "max_score": 5},
            {"key": "restoration_finish", "label": "Restoration Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_lighting_v1",
        "service_type": "lighting",
        "division": "Install",
        "title": "Lighting v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["wiring_exposed", "fixture_misfire"],
        "categories": [
            {"key": "placement_accuracy", "label": "Placement Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "function_test", "label": "Function Test", "weight": 0.33, "max_score": 5},
            {"key": "concealment_finish", "label": "Concealment Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_removal_v1",
        "service_type": "removal",
        "division": "Tree",
        "title": "Removal v1",
        "version": 1,
        "min_photos": 4,
        "pass_threshold": 84,
        "hard_fail_conditions": ["unsafe_drop_zone", "debris_left_behind"],
        "categories": [
            {"key": "safety_execution", "label": "Safety Execution", "weight": 0.34, "max_score": 5},
            {"key": "debris_clearance", "label": "Debris Clearance", "weight": 0.33, "max_score": 5},
            {"key": "surface_protection", "label": "Surface Protection", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_stump_grinding_v1",
        "service_type": "stump grinding",
        "division": "Tree",
        "title": "Stump Grinding v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["stump_remaining", "surface_damage"],
        "categories": [
            {"key": "grind_completeness", "label": "Grind Completeness", "weight": 0.34, "max_score": 5},
            {"key": "debris_containment", "label": "Debris Containment", "weight": 0.33, "max_score": 5},
            {"key": "surface_finish", "label": "Surface Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_fert_and_chem_treatments_v1",
        "service_type": "fert and chem treatments",
        "division": "Plant Healthcare",
        "title": "Fert and Chem Treatments v1",
        "version": 1,
        "min_photos": 2,
        "pass_threshold": 85,
        "hard_fail_conditions": ["label_noncompliance", "unsafe_application"],
        "categories": [
            {"key": "coverage_accuracy", "label": "Coverage Accuracy", "weight": 0.34, "max_score": 5},
            {"key": "safety_compliance", "label": "Safety Compliance", "weight": 0.33, "max_score": 5},
            {"key": "record_clarity", "label": "Record Clarity", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_air_spade_v1",
        "service_type": "air spade",
        "division": "Plant Healthcare",
        "title": "Air Spade v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["root_damage", "unsafe_excavation"],
        "categories": [
            {"key": "root_zone_care", "label": "Root Zone Care", "weight": 0.34, "max_score": 5},
            {"key": "excavation_control", "label": "Excavation Control", "weight": 0.33, "max_score": 5},
            {"key": "restoration_finish", "label": "Restoration Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_dormant_pruning_v1",
        "service_type": "dormant pruning",
        "division": "Plant Healthcare",
        "title": "Dormant Pruning v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["bud_damage", "unsafe_cutting_practice"],
        "categories": [
            {"key": "pruning_intent", "label": "Pruning Intent", "weight": 0.34, "max_score": 5},
            {"key": "plant_health_protection", "label": "Plant Health Protection", "weight": 0.33, "max_score": 5},
            {"key": "cleanup_finish", "label": "Cleanup Finish", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_deer_fencing_and_shrub_treatment_v1",
        "service_type": "deer fencing and shrub treatment",
        "division": "Plant Healthcare",
        "title": "Deer Fencing and Shrub Treatment v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 83,
        "hard_fail_conditions": ["coverage_gap", "plant_damage"],
        "categories": [
            {"key": "protection_coverage", "label": "Protection Coverage", "weight": 0.34, "max_score": 5},
            {"key": "treatment_quality", "label": "Treatment Quality", "weight": 0.33, "max_score": 5},
            {"key": "final_presentation", "label": "Final Presentation", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_snow_removal_v1",
        "service_type": "snow removal",
        "division": "Winter Services",
        "title": "Snow Removal v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 85,
        "hard_fail_conditions": ["unsafe_walkway", "missed_access_lane"],
        "categories": [
            {"key": "surface_coverage", "label": "Surface Coverage", "weight": 0.34, "max_score": 5},
            {"key": "access_safety", "label": "Access Safety", "weight": 0.33, "max_score": 5},
            {"key": "pile_placement", "label": "Pile Placement", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_plow_v1",
        "service_type": "plow",
        "division": "Winter Services",
        "title": "Plow v1",
        "version": 1,
        "min_photos": 3,
        "pass_threshold": 84,
        "hard_fail_conditions": ["missed_route", "curb_damage"],
        "categories": [
            {"key": "route_completeness", "label": "Route Completeness", "weight": 0.34, "max_score": 5},
            {"key": "obstruction_control", "label": "Obstruction Control", "weight": 0.33, "max_score": 5},
            {"key": "final_surface", "label": "Final Surface", "weight": 0.33, "max_score": 5},
        ],
    },
    {
        "id": "rubric_salting_v1",
        "service_type": "salting",
        "division": "Winter Services",
        "title": "Salting v1",
        "version": 1,
        "min_photos": 2,
        "pass_threshold": 85,
        "hard_fail_conditions": ["untreated_hazard_zone", "material_overuse"],
        "categories": [
            {"key": "coverage_consistency", "label": "Coverage Consistency", "weight": 0.34, "max_score": 5},
            {"key": "slip_risk_reduction", "label": "Slip-Risk Reduction", "weight": 0.33, "max_score": 5},
            {"key": "material_control", "label": "Material Control", "weight": 0.33, "max_score": 5},
        ],
    },
]


async def seed_defaults() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    users = [
        {"name": "Johnny H", "email": "HJohnny.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Craig S", "email": "SCraig.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Fran P", "email": "PFran.Super@SLMCo.local", "role": "management", "title": "Supervisor"},
        {"name": "Scott K", "email": "KScott.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Megan B", "email": "BMegan.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Daniel M", "email": "MDaniel.AccM@SLMCo.local", "role": "management", "title": "Account Manager"},
        {"name": "Tim A", "email": "ATim.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Zach O", "email": "OZach.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Scott W", "email": "WScott.ProM@SLMCo.local", "role": "management", "title": "Production Manager"},
        {"name": "Tyler C", "email": "CTyler.GM@SLMCo.local", "role": "management", "title": "GM"},
        {"name": "Brad S", "email": "SBrad.GM@SLMCo.local", "role": "management", "title": "GM"},
        {"name": "Adam S", "email": "SAdam.Owner@SLMCo.local", "role": "owner", "title": "Owner"},
    ]
    for user in users:
        email_lower = user["email"].lower()
        existing = await db.users.find_one({"email": email_lower}, {"_id": 0})
        if existing:
            await db.users.update_one(
                {"email": email_lower},
                {
                    "$set": {
                        "name": user["name"],
                        "role": user["role"],
                        "title": user["title"],
                        "is_active": True,
                        "updated_at": now_iso(),
                    }
                },
            )
        else:
            await db.users.delete_many({"email": {"$regex": f"^{user['email']}$", "$options": "i"}})
            await db.users.insert_one(
                {
                    "id": make_id("user"),
                    **{**user, "email": email_lower},
                    "password_hash": get_password_hash("SLMCo2026!"),
                    "is_active": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", f"{user['title']} demo account created")],
                }
            )

    await db.jobs.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.crew_access_links.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})
    await db.submissions.update_many({"division": "Cleanup"}, {"$set": {"division": "Maintenance", "updated_at": now_iso()}})

    for rubric in RUBRIC_LIBRARY:
        existing = await db.rubric_definitions.find_one({"service_type": rubric["service_type"].lower(), "version": rubric["version"]}, {"_id": 0})
        document = {
            **rubric,
            "service_type": rubric["service_type"].lower(),
            "is_active": True,
            "created_at": existing.get("created_at", now_iso()) if existing else now_iso(),
            "updated_at": now_iso(),
            "audit_history": existing.get("audit_history", [audit_entry("seeded", "system", f"Rubric {rubric['title']} loaded")]) if existing else [audit_entry("seeded", "system", f"Rubric {rubric['title']} loaded")],
        }
        await db.rubric_definitions.update_one(
            {"service_type": rubric["service_type"].lower(), "version": rubric["version"]},
            {"$set": document},
            upsert=True,
        )

    if await db.crew_access_links.count_documents({}) == 0:
        crew_links = [
            {"label": "North Crew", "truck_number": "TR-12", "division": "Install"},
            {"label": "Central Crew", "truck_number": "TR-18", "division": "Maintenance"},
            {"label": "South Crew", "truck_number": "TR-24", "division": "Cleanup"},
        ]
        await db.crew_access_links.insert_many(
            [
                {
                    "id": make_id("crew"),
                    "code": uuid.uuid4().hex[:8],
                    "crew_member_id": make_id("crewid").upper(),
                    **item,
                    "enabled": True,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "audit_history": [audit_entry("seeded", "system", "Crew QR access created")],
                }
                for item in crew_links
            ]
        )

    if await db.jobs.count_documents({}) == 0:
        jobs = [
            {
                "id": make_id("job"),
                "job_id": "LMN-4101",
                "job_name": "Riverview Estates Entry Beds",
                "property_name": "Riverview Estates",
                "address": "101 Riverside Dr",
                "service_type": "bed edging",
                "scheduled_date": (utc_now() + timedelta(days=1)).isoformat(),
                "division": "Install",
                "truck_number": "TR-12",
                "route": "North Route",
                "source": "seed",
                "search_text": "lmn-4101 riverview estates entry beds",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
            {
                "id": make_id("job"),
                "job_id": "LMN-4102",
                "job_name": "Maple Grove Spring Reset",
                "property_name": "Maple Grove HOA",
                "address": "55 Maple Grove Ln",
                "service_type": "spring cleanup",
                "scheduled_date": utc_now().isoformat(),
                "division": "Maintenance",
                "truck_number": "TR-18",
                "route": "Central Route",
                "source": "seed",
                "search_text": "lmn-4102 maple grove spring cleanup",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
            {
                "id": make_id("job"),
                "job_id": "LMN-4103",
                "job_name": "Willow Creek Fall Cleanup",
                "property_name": "Willow Creek Office Park",
                "address": "880 Willow Pkwy",
                "service_type": "fall cleanup",
                "scheduled_date": (utc_now() - timedelta(days=1)).isoformat(),
                "division": "Cleanup",
                "truck_number": "TR-24",
                "route": "South Route",
                "source": "seed",
                "search_text": "lmn-4103 willow creek fall cleanup",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", "system", "Seed job loaded")],
            },
        ]
        await db.jobs.insert_many(jobs)

    if await db.submissions.count_documents({}) == 0:
        jobs = await db.jobs.find({}, {"_id": 0}).to_list(10)
        crew_links = await db.crew_access_links.find({}, {"_id": 0}).to_list(10)
        if jobs and crew_links:
            ready_job = jobs[0]
            reviewed_job = jobs[1]
            finalized_job = jobs[2]
            ready_submission_id = make_id("sub")
            reviewed_submission_id = make_id("sub")
            finalized_submission_id = make_id("sub")

            photo_urls = [
                "https://images.pexels.com/photos/6728925/pexels-photo-6728925.jpeg?auto=compress&cs=tinysrgb&w=1200",
                "https://images.unsplash.com/photo-1696663118264-55a63c75409b?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "https://images.unsplash.com/photo-1605117882932-f9e32b03fea9?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
            ]

            def make_seed_submission(sub_id, job, crew_link, status, note, area_tag, days_ago, issue_type="", issue_notes=""):
                ts = (utc_now() - timedelta(days=days_ago)).isoformat()
                work_d = (utc_now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
                return {
                    "id": sub_id, "submission_code": sub_id.upper(),
                    "access_code": crew_link["code"], "crew_label": crew_link["label"],
                    "job_id": job["job_id"], "job_name_input": job.get("job_name", job["job_id"]),
                    "matched_job_id": job["id"], "match_status": "confirmed", "match_confidence": 0.92,
                    "truck_number": job["truck_number"], "division": job["division"],
                    "service_type": job["service_type"], "task_type": job["service_type"],
                    "status": status, "note": note, "area_tag": area_tag,
                    "field_report": {"type": issue_type, "notes": issue_notes, "photo_files": [], "reported": bool(issue_type)},
                    "gps": {"lat": 43.631 + (days_ago % 10) * 0.001, "lng": -79.412 + (days_ago % 7) * 0.001, "accuracy": 7},
                    "work_date": work_d, "captured_at": ts,
                    "photo_count": 3, "required_photo_count": 3,
                    "photo_files": [{"id": make_id("file"), "filename": f"seed-{sub_id[-6:]}-1.jpg", "mime_type": "image/jpeg", "sequence": 1, "source_type": "remote", "media_url": photo_urls[days_ago % len(photo_urls)]}],
                    "storage_status": "seed_remote",
                    "created_at": ts, "updated_at": ts,
                    "audit_history": [audit_entry("seeded", "system", "Sample submission created")],
                }

            samples = [
                make_seed_submission(ready_submission_id, ready_job, crew_links[0], "Ready for Review", "Seeded sample awaiting management scoring", "Front entry", 1),
                make_seed_submission(reviewed_submission_id, reviewed_job, crew_links[1], "Management Reviewed", "Cleanup completed with minor clippings left in curb line", "Parking edge", 5),
                make_seed_submission(finalized_submission_id, finalized_job, crew_links[2], "Export Ready", "Owner-approved gold sample", "Rear drainage swale", 10),
            ]

            issue_types = ["curb_line_cleanup", "edge_quality", "debris_left", "incomplete_mulch", "pruning_damage", "missed_area"]
            statuses = ["Ready for Review", "Management Reviewed", "Management Reviewed", "Management Reviewed"]
            notes = ["Minor issues found during review", "Missed section along north fence", "Inconsistent edge depth", "Debris left on walkway", "Pruning cuts too aggressive", "Mulch layer too thin near beds"]
            areas = ["Front entry", "Side lot", "Parking edge", "Rear beds", "North fence line", "Main walkway"]
            num_crews = min(len(crew_links), 5)
            num_jobs = min(len(jobs), 3)
            for i in range(20):
                sub_id = make_id("sub")
                days_ago = int((i / 20) * 240) + 2
                crew = crew_links[i % num_crews]
                job = jobs[i % num_jobs]
                has_issue = i % 3 != 0
                samples.append(make_seed_submission(
                    sub_id, job, crew,
                    statuses[i % len(statuses)],
                    notes[i % len(notes)], areas[i % len(areas)], days_ago,
                    issue_type=issue_types[i % len(issue_types)] if has_issue else "",
                    issue_notes=f"Seed issue for repeat offender testing ({days_ago} days ago)" if has_issue else "",
                ))

            await db.submissions.insert_many(samples)

            management_user = await db.users.find_one({"role": "management"}, {"_id": 0})
            owner_user = await db.users.find_one({"role": "owner"}, {"_id": 0})
            spring_rubric = await get_active_rubric("spring cleanup")
            fall_rubric = await get_active_rubric("fall cleanup")
            management_review = {
                "id": make_id("mgr"),
                "submission_id": reviewed_submission_id,
                "reviewer_id": management_user["id"],
                "rubric_id": spring_rubric["id"],
                "rubric_version": spring_rubric["version"],
                "service_type": "spring cleanup",
                "category_scores": {"coverage": 4, "cleanliness": 4, "bed_definition": 3, "turf_finish": 4, "curb_appeal": 4},
                "total_score": 77.6,
                "comments": "Good reset overall, minor curb clippings remain.",
                "disposition": "pass with notes",
                "flagged_issues": ["curb_line_cleanup"],
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", management_user["id"], "Seed management review")],
            }
            owner_review = {
                "id": make_id("own"),
                "submission_id": finalized_submission_id,
                "reviewer_id": owner_user["id"],
                "rubric_id": fall_rubric["id"],
                "rubric_version": fall_rubric["version"],
                "service_type": "fall cleanup",
                "category_scores": {"leaf_removal": 5, "detail_finish": 4, "bed_cleanup": 4, "walkway_clearance": 5, "visual_finish": 4},
                "total_score": 90.8,
                "comments": "Excellent gold-standard cleanup example.",
                "final_disposition": "pass",
                "training_inclusion": "approved",
                "exclusion_reason": "",
                "variance_from_management": 2.4,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "audit_history": [audit_entry("seeded", owner_user["id"], "Seed owner review")],
            }
            await db.management_reviews.insert_one(management_review)
            await db.owner_reviews.insert_one(owner_review)

            rapid_reviews_seed = []
            issue_tags = ["curb_line_cleanup", "edge_quality", "debris_left", "incomplete_mulch", "pruning_damage", "missed_area"]
            ratings = ["fail", "concern", "concern", "fail", "concern", "standard"]
            for i, sub in enumerate(samples[3:]):
                days_ago = int((i / 20) * 240) + 2
                ts = (utc_now() - timedelta(days=days_ago)).isoformat()
                has_issue = i % 3 != 0
                if has_issue:
                    rapid_reviews_seed.append({
                        "id": make_id("rr"),
                        "submission_id": sub["id"],
                        "reviewer_id": management_user["id"],
                        "overall_rating": ratings[i % len(ratings)],
                        "issue_tag": issue_tags[i % len(issue_tags)],
                        "remark": f"Seed rapid review for testing ({days_ago} days ago)",
                        "time_spent_ms": 4500 + (i * 300),
                        "created_at": ts,
                        "updated_at": ts,
                        "audit_history": [audit_entry("seeded", management_user["id"], "Seed rapid review")],
                    })
            if rapid_reviews_seed:
                await db.rapid_reviews.insert_many(rapid_reviews_seed)

    if await db.standards_library.count_documents({}) == 0:
        standards = [
            {
                "id": make_id("std"),
                "title": "Clean bed edge finish",
                "category": "Edging",
                "audience": "crew",
                "division_targets": ["Maintenance", "Install"],
                "checklist": ["Edge line reads clean", "No turf spill", "Street-facing finish shot included"],
                "notes": "Use one wide establishing shot and one close-up of the edge line.",
                "owner_notes": "Great baseline example for edging crews.",
                "shoutout": "@North Crew",
                "image_url": "https://images.unsplash.com/photo-1734303023491-db8037a21f09?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "Which result best matches this standard?",
                "choice_options": ["Street-ready edge", "Needs more cleanup", "Unsafe site"],
                "correct_answer": "Street-ready edge",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Mulch bed cleanliness",
                "category": "Mulch",
                "audience": "crew",
                "division_targets": ["Install", "Maintenance"],
                "checklist": ["Mulch kept out of turf", "Bed edge visible", "Depth looks even"],
                "notes": "Capture texture and edge definition together.",
                "owner_notes": "Use for install coaching when edges are lost.",
                "shoutout": "@Install Team",
                "image_url": "https://images.pexels.com/photos/30467599/pexels-photo-30467599.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "What should a reviewer confirm first?",
                "choice_options": ["Depth consistency", "Truck number", "Weather"],
                "correct_answer": "Depth consistency",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Cleanup completion proof",
                "category": "Cleanup",
                "audience": "crew",
                "division_targets": ["Maintenance", "PHC - Plant Healthcare"],
                "checklist": ["Debris removed", "Walks clear", "Final condition is obvious"],
                "notes": "Use a final shot that clearly proves the reset is complete.",
                "owner_notes": "Best used for spring/fall cleanups.",
                "shoutout": "@Cleanup Team",
                "image_url": "https://images.unsplash.com/photo-1734079692160-fcbe4be6ab96?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "free_text",
                "question_prompt": "In one phrase, what makes this proof set feel complete?",
                "choice_options": [],
                "correct_answer": "clear final condition|final condition is obvious|complete reset",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": make_id("std"),
                "title": "Tree pruning clarity",
                "category": "Pruning",
                "audience": "crew",
                "division_targets": ["Sarver Tree"],
                "checklist": ["Cut area visible", "Safety zone clear", "Final canopy view shown"],
                "notes": "Always show both the cut detail and the cleared zone.",
                "owner_notes": "Tree division standard example.",
                "shoutout": "@Tree Crew",
                "image_url": "https://images.unsplash.com/photo-1772764057845-121fd5f3ebe8?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
                "training_enabled": True,
                "question_type": "multiple_choice",
                "question_prompt": "Which extra image should always be included with pruning work?",
                "choice_options": ["Safety zone clear shot", "Truck dashboard", "Sky only"],
                "correct_answer": "Safety zone clear shot",
                "is_active": True,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        ]
        await db.standards_library.insert_many(standards)


@app.on_event("startup")
async def startup_event():
    await seed_defaults()
    await db.rapid_reviews.create_index("submission_id", unique=True)
    await db.rapid_review_sessions.create_index("reviewer_id")
    await db.rapid_review_sessions.create_index("created_at")
    await db.standards_library.create_index("id", unique=True)
    await db.training_sessions.create_index("code", unique=True)
    if storage_is_configured():
        try:
            get_supabase_client()
            logger.info("Supabase storage client initialized")
        except Exception as exc:
            logger.error("Supabase storage initialization failed: %s", exc)


# ── Include all route modules ──────────────────────────────────────────
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(public_router)
api_router.include_router(submissions_router)
api_router.include_router(equipment_router)
api_router.include_router(jobs_router)
api_router.include_router(crew_access_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
api_router.include_router(rubrics_router)
api_router.include_router(standards_router)
api_router.include_router(reviews_router)
api_router.include_router(rapid_reviews_router)
api_router.include_router(training_router)
api_router.include_router(analytics_router)
api_router.include_router(exports_router)
api_router.include_router(integrations_router)
api_router.include_router(reviewer_performance_router)
api_router.include_router(coaching_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

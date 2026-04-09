"""Expand rubrics and standards to cover all real landscaping divisions and tasks."""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "sarver_landscape")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ── New Rubric Definitions ──────────────────────────────────────────────
NEW_RUBRICS = [
    # Enhancement division
    {
        "id": "rubric_seasonal_color_v1", "service_type": "seasonal color",
        "title": "Seasonal Color Installation", "division": "Enhancement", "is_active": True, "version": 1,
        "categories": [
            {"key": "color_pattern", "label": "Color Pattern & Design", "weight": 0.25, "max_score": 5, "fail_clue": "No discernible pattern", "top_clue": "Creative, balanced color blocking"},
            {"key": "plant_health", "label": "Plant Health & Selection", "weight": 0.25, "max_score": 5, "fail_clue": "Dead or wilted annuals installed", "top_clue": "Full blooms, uniform sizing"},
            {"key": "spacing", "label": "Plant Spacing & Depth", "weight": 0.2, "max_score": 5, "fail_clue": "Crowded or too sparse", "top_clue": "Even, textbook spacing"},
            {"key": "bed_prep", "label": "Bed Preparation", "weight": 0.15, "max_score": 5, "fail_clue": "Weeds remain, no soil amendment", "top_clue": "Clean bed, amended soil"},
            {"key": "cleanup", "label": "Site Cleanup", "weight": 0.15, "max_score": 5, "fail_clue": "Containers and debris left on site", "top_clue": "Spotless, client-ready"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_landscape_design_v1", "service_type": "landscape design enhancement",
        "title": "Landscape Design Enhancement", "division": "Enhancement", "is_active": True, "version": 1,
        "categories": [
            {"key": "design_adherence", "label": "Design Plan Adherence", "weight": 0.3, "max_score": 5, "fail_clue": "Wrong plant species or placement", "top_clue": "Exact match to approved design"},
            {"key": "grading", "label": "Grade & Drainage", "weight": 0.2, "max_score": 5, "fail_clue": "Ponding or negative grade", "top_clue": "Positive drainage, smooth contours"},
            {"key": "planting_quality", "label": "Planting Quality", "weight": 0.25, "max_score": 5, "fail_clue": "Root balls exposed or too deep", "top_clue": "Crown at grade, proper mulch ring"},
            {"key": "material_quality", "label": "Material Quality", "weight": 0.15, "max_score": 5, "fail_clue": "Damaged or incorrect materials", "top_clue": "Premium materials, no substitutions"},
            {"key": "final_presentation", "label": "Final Presentation", "weight": 0.1, "max_score": 5, "fail_clue": "Unfinished look", "top_clue": "Magazine-ready finish"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    # Irrigation division
    {
        "id": "rubric_irrigation_repair_v1", "service_type": "irrigation repair",
        "title": "Irrigation System Repair", "division": "Irrigation", "is_active": True, "version": 1,
        "categories": [
            {"key": "diagnosis", "label": "Issue Diagnosis", "weight": 0.2, "max_score": 5, "fail_clue": "Wrong root cause identified", "top_clue": "Accurate, documented diagnosis"},
            {"key": "repair_quality", "label": "Repair Quality", "weight": 0.3, "max_score": 5, "fail_clue": "Leak persists post-repair", "top_clue": "Leak-free, pressure tested"},
            {"key": "coverage", "label": "Head Coverage & Adjustment", "weight": 0.25, "max_score": 5, "fail_clue": "Dry spots or overspray on hardscape", "top_clue": "Head-to-head coverage, zero overspray"},
            {"key": "backfill", "label": "Trench Backfill & Restoration", "weight": 0.15, "max_score": 5, "fail_clue": "Open trenches, loose soil", "top_clue": "Flush grade, re-sodded or seeded"},
            {"key": "documentation", "label": "Before/After Documentation", "weight": 0.1, "max_score": 5, "fail_clue": "No before photos", "top_clue": "Before, during, after sequence"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_winterization_v1", "service_type": "winterization",
        "title": "Irrigation Winterization", "division": "Irrigation", "is_active": True, "version": 1,
        "categories": [
            {"key": "blowout_procedure", "label": "Air Blowout Procedure", "weight": 0.35, "max_score": 5, "fail_clue": "Water remaining in lines", "top_clue": "Full evacuation confirmed"},
            {"key": "controller", "label": "Controller Shutoff & Backup", "weight": 0.2, "max_score": 5, "fail_clue": "Controller left running", "top_clue": "Rain mode set, schedule backed up"},
            {"key": "valve_tags", "label": "Valve & Backflow Tagging", "weight": 0.2, "max_score": 5, "fail_clue": "No tags, unclear valve map", "top_clue": "All valves labeled, backflow drained"},
            {"key": "client_comm", "label": "Client Communication", "weight": 0.15, "max_score": 5, "fail_clue": "No service tag left", "top_clue": "Door tag + email confirmation"},
            {"key": "site_cleanup", "label": "Site Cleanup", "weight": 0.1, "max_score": 5, "fail_clue": "Hoses/fittings left on site", "top_clue": "Equipment removed, site spotless"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_spring_startup_v1", "service_type": "spring startup",
        "title": "Irrigation Spring Startup", "division": "Irrigation", "is_active": True, "version": 1,
        "categories": [
            {"key": "system_check", "label": "Full System Walkthrough", "weight": 0.3, "max_score": 5, "fail_clue": "Zones skipped", "top_clue": "All zones verified, timed"},
            {"key": "head_adjustment", "label": "Head Adjustment & Cleaning", "weight": 0.25, "max_score": 5, "fail_clue": "Clogged or misaligned heads", "top_clue": "All heads clean, arc correct"},
            {"key": "leak_detection", "label": "Leak Detection", "weight": 0.25, "max_score": 5, "fail_clue": "Leak missed during walkthrough", "top_clue": "Zero leaks, pressure stable"},
            {"key": "controller_program", "label": "Controller Programming", "weight": 0.15, "max_score": 5, "fail_clue": "Old schedule still running", "top_clue": "Season-appropriate schedule set"},
            {"key": "report", "label": "Service Report", "weight": 0.05, "max_score": 5, "fail_clue": "No report generated", "top_clue": "Detailed zone-by-zone report"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    # Missing Maintenance tasks
    {
        "id": "rubric_aeration_v1", "service_type": "aeration",
        "title": "Core Aeration", "division": "Maintenance", "is_active": True, "version": 1,
        "categories": [
            {"key": "depth", "label": "Core Depth & Spacing", "weight": 0.3, "max_score": 5, "fail_clue": "Shallow cores, wide spacing", "top_clue": "2-3 inch cores, tight pattern"},
            {"key": "coverage", "label": "Full Lawn Coverage", "weight": 0.3, "max_score": 5, "fail_clue": "Missed areas visible", "top_clue": "Edge-to-edge, overlapping passes"},
            {"key": "obstacle_nav", "label": "Obstacle Navigation", "weight": 0.2, "max_score": 5, "fail_clue": "Sprinkler heads or lines hit", "top_clue": "Clean around all obstacles"},
            {"key": "cleanup", "label": "Site Cleanup", "weight": 0.2, "max_score": 5, "fail_clue": "Cores on hardscape", "top_clue": "Walks and drives blown clean"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_overseeding_v1", "service_type": "overseeding",
        "title": "Overseeding Application", "division": "Maintenance", "is_active": True, "version": 1,
        "categories": [
            {"key": "seed_rate", "label": "Seed Rate & Distribution", "weight": 0.3, "max_score": 5, "fail_clue": "Clumps or bare spots", "top_clue": "Even broadcast, correct rate"},
            {"key": "seed_contact", "label": "Seed-to-Soil Contact", "weight": 0.3, "max_score": 5, "fail_clue": "Seed sitting on thatch", "top_clue": "Aeration + topdressing combo"},
            {"key": "species_match", "label": "Seed Species Match", "weight": 0.2, "max_score": 5, "fail_clue": "Wrong species for conditions", "top_clue": "Site-appropriate cultivar blend"},
            {"key": "watering_instructions", "label": "Client Watering Instructions", "weight": 0.2, "max_score": 5, "fail_clue": "No watering guide provided", "top_clue": "Written schedule left with client"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_turf_mowing_v1", "service_type": "turf mowing",
        "title": "Turf Mowing", "division": "Maintenance", "is_active": True, "version": 1,
        "categories": [
            {"key": "cut_height", "label": "Cut Height Accuracy", "weight": 0.25, "max_score": 5, "fail_clue": "Scalped or too high", "top_clue": "Consistent height, 1/3 rule followed"},
            {"key": "stripe_pattern", "label": "Stripe Pattern & Direction", "weight": 0.2, "max_score": 5, "fail_clue": "No alternating pattern", "top_clue": "Clean alternating stripes"},
            {"key": "trim_edging", "label": "Trimming & Edging", "weight": 0.25, "max_score": 5, "fail_clue": "Missed trim areas around obstacles", "top_clue": "Crisp edges, clean around all beds"},
            {"key": "clipping_mgmt", "label": "Clipping Management", "weight": 0.15, "max_score": 5, "fail_clue": "Clumps left on lawn", "top_clue": "Dispersed evenly or collected"},
            {"key": "hardscape_cleanup", "label": "Hardscape Blowoff", "weight": 0.15, "max_score": 5, "fail_clue": "Clippings on walks/drives", "top_clue": "All surfaces clean"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    # Missing Install tasks
    {
        "id": "rubric_retaining_wall_v1", "service_type": "retaining wall",
        "title": "Retaining Wall Construction", "division": "Install", "is_active": True, "version": 1,
        "categories": [
            {"key": "base_prep", "label": "Base Preparation", "weight": 0.25, "max_score": 5, "fail_clue": "Insufficient base depth or compaction", "top_clue": "6+ inch compacted base"},
            {"key": "level_plumb", "label": "Level & Plumb", "weight": 0.25, "max_score": 5, "fail_clue": "Visible lean or waviness", "top_clue": "True to plan, tight joints"},
            {"key": "drainage_behind", "label": "Drainage Behind Wall", "weight": 0.2, "max_score": 5, "fail_clue": "No drain tile or gravel", "top_clue": "Full drain system with fabric"},
            {"key": "cap_finish", "label": "Cap & Finish", "weight": 0.15, "max_score": 5, "fail_clue": "Uneven cap, excess adhesive", "top_clue": "Clean cap line, adhesive hidden"},
            {"key": "geogrid", "label": "Geogrid Placement", "weight": 0.15, "max_score": 5, "fail_clue": "Missing geogrid on walls over 3ft", "top_clue": "Grid at spec intervals"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_paver_patio_v1", "service_type": "paver patio",
        "title": "Paver Patio Installation", "division": "Install", "is_active": True, "version": 1,
        "categories": [
            {"key": "excavation", "label": "Excavation & Subgrade", "weight": 0.2, "max_score": 5, "fail_clue": "Shallow dig, organic material left", "top_clue": "Proper depth, clean subgrade"},
            {"key": "base_compaction", "label": "Base & Compaction", "weight": 0.2, "max_score": 5, "fail_clue": "Soft spots, uneven grade", "top_clue": "Plate-compacted, laser-checked"},
            {"key": "pattern_layout", "label": "Pattern & Layout", "weight": 0.2, "max_score": 5, "fail_clue": "Pattern breaks, wrong orientation", "top_clue": "Consistent pattern, centered cuts"},
            {"key": "edge_restraint", "label": "Edge Restraint", "weight": 0.2, "max_score": 5, "fail_clue": "Missing or loose edge", "top_clue": "Spiked restraint, flush with pavers"},
            {"key": "joint_sand", "label": "Joint Sand & Sealing", "weight": 0.2, "max_score": 5, "fail_clue": "Empty joints, no poly sand", "top_clue": "Full joints, properly activated"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    # Missing Tree tasks
    {
        "id": "rubric_canopy_lift_v1", "service_type": "canopy lifting",
        "title": "Canopy Lifting / Clearance Pruning", "division": "Tree", "is_active": True, "version": 1,
        "categories": [
            {"key": "clearance_height", "label": "Clearance Height Achieved", "weight": 0.3, "max_score": 5, "fail_clue": "Below spec clearance", "top_clue": "Meets or exceeds spec"},
            {"key": "cut_quality", "label": "Cut Quality (ISA Standard)", "weight": 0.3, "max_score": 5, "fail_clue": "Flush cuts or stubs", "top_clue": "Proper branch collar cuts"},
            {"key": "crown_balance", "label": "Crown Balance", "weight": 0.2, "max_score": 5, "fail_clue": "Lopsided or lion-tailed", "top_clue": "Balanced, natural silhouette"},
            {"key": "debris_cleanup", "label": "Debris Cleanup", "weight": 0.2, "max_score": 5, "fail_clue": "Branches left on site", "top_clue": "Complete removal, area raked"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
    {
        "id": "rubric_cabling_bracing_v1", "service_type": "cabling and bracing",
        "title": "Tree Cabling & Bracing", "division": "Tree", "is_active": True, "version": 1,
        "categories": [
            {"key": "hardware_placement", "label": "Hardware Placement", "weight": 0.3, "max_score": 5, "fail_clue": "Too low or wrong attachment", "top_clue": "2/3 height, proper J-lags"},
            {"key": "cable_tension", "label": "Cable Tension", "weight": 0.3, "max_score": 5, "fail_clue": "Too tight (girdling) or too slack", "top_clue": "Proper sag, allows movement"},
            {"key": "tree_health", "label": "Tree Health Assessment", "weight": 0.2, "max_score": 5, "fail_clue": "No assessment documented", "top_clue": "Full risk assessment on file"},
            {"key": "documentation", "label": "Installation Documentation", "weight": 0.2, "max_score": 5, "fail_clue": "No photos or specs recorded", "top_clue": "Before/after with specs"},
        ],
        "hard_fail_conditions": ["no_image_captured", "improper_image_quality"],
    },
]

# ── New Standards ─────────────────────────────────────────────────────────
NEW_STANDARDS = [
    {
        "id": f"std_irrigation_repair",
        "title": "Irrigation Repair — Diagnosis & Fix Documentation",
        "category": "Irrigation",
        "rules": [
            "Photograph the problem area before any excavation or repair begins.",
            "Document the root cause (broken head, cracked lateral, valve failure, etc.).",
            "Show repair materials and method (glue joints, clamp repairs, replacement heads).",
            "Run each repaired zone for 2+ minutes and photograph head coverage.",
            "Backfill trenches flush with grade and resod or seed exposed turf.",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
    {
        "id": f"std_seasonal_color",
        "title": "Seasonal Color — Annual Bed Installation Standards",
        "category": "Seasonal Color",
        "rules": [
            "Prepare beds by removing prior season's annuals, amending soil, and raking smooth.",
            "Follow the approved design plan for species, color blocking, and spacing.",
            "Plant at proper depth — root ball top flush with soil grade.",
            "Water in all new plantings before leaving the job site.",
            "Remove all containers, tags, and packaging from the property.",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
    {
        "id": f"std_turf_mowing",
        "title": "Turf Mowing — Cut Quality & Pattern Standards",
        "category": "Turf Mowing",
        "rules": [
            "Follow the 1/3 rule — never remove more than one-third of the blade height.",
            "Alternate mowing direction each visit to prevent rut formation.",
            "String-trim around all beds, trees, fences, and hardscape edges.",
            "Blow all clippings off hardscape surfaces (walks, drives, patios).",
            "Report any turf disease, bare patches, or irrigation issues to the PM.",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
    {
        "id": f"std_retaining_wall",
        "title": "Retaining Wall — Structural & Aesthetic Standards",
        "category": "Retaining Wall",
        "rules": [
            "Excavate to proper depth based on wall height spec (min 6-inch compacted base).",
            "Install drain tile and drainage aggregate behind all walls over 12 inches.",
            "Level each course with a 4-foot level — max 1/8 inch variance per 4 feet.",
            "Install geogrid at manufacturer-specified intervals for walls over 3 feet.",
            "Cap blocks must be adhesived and flush — no overhang or adhesive squeeze-out visible.",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
    {
        "id": f"std_aeration",
        "title": "Core Aeration — Lawn Health Standards",
        "category": "Aeration",
        "rules": [
            "Mark all sprinkler heads, shallow utilities, and invisible fence wires before starting.",
            "Achieve 2-3 inch core depth with 3-inch spacing between holes.",
            "Make two passes in perpendicular directions for maximum coverage.",
            "Leave cores on the lawn to decompose — do not remove.",
            "Blow all cores off hardscape surfaces (walks, drives, patios).",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
    {
        "id": f"std_canopy_lifting",
        "title": "Canopy Lifting — ISA Clearance Pruning Standards",
        "category": "Canopy Lifting",
        "rules": [
            "Establish target clearance height with PM before starting (typically 8-10 ft for pedestrian, 14 ft for vehicle).",
            "Use proper three-cut method on branches over 2 inches to prevent bark tearing.",
            "Cut to the branch collar — no flush cuts or stubs.",
            "Never remove more than 25% of the live crown in a single session.",
            "Chip or haul all debris — rake the drip line area clean before leaving.",
        ],
        "images": [],
        "is_active": True,
        "created_at": now_iso(),
    },
]


async def main():
    print("=== RUBRIC & STANDARDS EXPANSION ===\n")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Clean up test rubric entries
    test_patterns = ["test_owner_service", "test_custom_service", "test_iter11_service", "test_delete_service", "test grading"]
    result = await db.rubric_definitions.delete_many({"service_type": {"$in": test_patterns}})
    print(f"[Cleanup] Removed {result.deleted_count} test rubric entries")

    # Insert new rubrics
    for rubric in NEW_RUBRICS:
        rubric["created_at"] = now_iso()
        rubric["updated_at"] = now_iso()
        rubric["audit_history"] = [{"timestamp": now_iso(), "action": "created", "note": f"{rubric['title']} loaded"}]
        await db.rubric_definitions.update_one({"id": rubric["id"]}, {"$set": rubric}, upsert=True)
        print(f"  Rubric: {rubric['service_type']:30s} ({rubric['division']})")

    # Insert new standards
    for std in NEW_STANDARDS:
        await db.standards_library.update_one({"id": std["id"]}, {"$set": std}, upsert=True)
        print(f"  Standard: {std['title'][:50]}...")

    # Summary
    total_rubrics = await db.rubric_definitions.count_documents({"is_active": True})
    total_standards = await db.standards_library.count_documents({})
    print(f"\nTotal active rubrics: {total_rubrics}")
    print(f"Total standards: {total_standards}")

    # Show by division
    pipeline = [{"$match": {"is_active": True}}, {"$group": {"_id": "$division", "count": {"$sum": 1}, "types": {"$push": "$service_type"}}}]
    async for doc in db.rubric_definitions.aggregate(pipeline):
        print(f"  {doc['_id']:20s}: {doc['count']} rubrics — {doc['types']}")

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())

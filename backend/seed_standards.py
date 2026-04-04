"""
Seed real industry-standard landscaping standards into standards_library.
Removes all TEST entries and inserts production-ready entries.
Also updates demo crew with leader_name.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "sarver_landscape")

def make_id(prefix="std"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

STANDARDS = [
    # ── MAINTENANCE ──
    {
        "title": "Bed Edging — Clean Line Standard",
        "category": "Bed Edging",
        "division_targets": ["Maintenance"],
        "audience": "crew",
        "checklist": [
            "Edge line is confident and continuous — no wobble or skip marks",
            "Turf side is contained with no overhang into bed",
            "Bed side has a clean vertical cut 2-3 inches deep",
            "Soil debris is removed or blown back into bed, not left on turf",
            "Final pass reads clean from the street"
        ],
        "notes": "Bed edging is one of the most visible quality indicators on any maintenance property. Reviewers look for a sharp, confident line that shows crew discipline. Photograph the edge from a low angle to prove depth and consistency.",
        "image_url": "https://images.unsplash.com/photo-1738193830098-2d92352a1856?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the target depth for a standard bed edge cut?",
        "choice_options": ["1 inch", "2-3 inches", "4-5 inches", "Surface only"],
        "correct_answer": "2-3 inches",
    },
    {
        "title": "Spring Cleanup — Full Property Reset",
        "category": "Spring Cleanup",
        "division_targets": ["Maintenance"],
        "audience": "crew",
        "checklist": [
            "All leaf and debris cleared from beds, lawns, and hardscapes",
            "Perennial cutbacks completed — no brown material above crown",
            "Bed edges re-established or freshened",
            "First mow stripe or cut visible on turf",
            "Curb lines and walks blown clean"
        ],
        "notes": "Spring cleanup is the first impression of the season. Document with a wide establishing shot showing the full property reset, then detail shots of bed edges and cutbacks. The property should feel complete, not partial.",
        "image_url": "https://images.unsplash.com/photo-1759069953255-5c8f9f9912b9?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What does a complete spring cleanup NOT include?",
        "choice_options": ["Leaf removal", "Perennial cutbacks", "Fertilizer application", "Re-establishing bed edges"],
        "correct_answer": "Fertilizer application",
    },
    {
        "title": "Fall Cleanup — Leaf Removal & Bed Preparation",
        "category": "Fall Cleanup",
        "division_targets": ["Maintenance"],
        "audience": "crew",
        "checklist": [
            "Leaves removed from all turf, bed, and hardscape surfaces",
            "Beds blown out and dressed clean for winter dormancy",
            "Gutter lines cleared if within scope of service",
            "No leaf piles left behind fences or in corners",
            "Final blow-off of walks, drives, and curb areas"
        ],
        "notes": "Fall cleanup quality is measured by what's left behind — nothing. Use wide shots to show the full clear, and document any areas that were particularly heavy. Partial cleanups are unacceptable.",
        "image_url": "https://images.unsplash.com/photo-1628482283044-e5cc2f238de1?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What's the most important indicator of a complete fall cleanup?",
        "choice_options": ["Speed of completion", "No debris left in any area", "Number of bags filled", "Equipment used"],
        "correct_answer": "No debris left in any area",
    },
    {
        "title": "Pruning — Ornamental Shrub Standards",
        "category": "Pruning",
        "division_targets": ["Maintenance", "Plant Healthcare"],
        "audience": "crew",
        "checklist": [
            "Natural growth habit maintained — no box cuts unless specified",
            "Dead, diseased, and crossing branches removed first",
            "Cuts made at the node or branch collar — no stubs",
            "Ground beneath shrub is cleared of clippings",
            "Shape reads balanced from all visible angles"
        ],
        "notes": "Pruning is a horticultural skill, not just trimming. Reviewers check for natural form, clean cuts, and proper technique. Photograph the shrub from the client's view line, then one close-up of your cut quality.",
        "image_url": "https://images.unsplash.com/photo-1649427909612-353b0042ab79?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "Where should a pruning cut be made?",
        "choice_options": ["Middle of the branch", "At the node or branch collar", "Anywhere convenient", "At the base of the trunk"],
        "correct_answer": "At the node or branch collar",
    },
    {
        "title": "Mulch Application — Depth & Coverage",
        "category": "Mulching",
        "division_targets": ["Maintenance"],
        "audience": "crew",
        "checklist": [
            "Mulch applied at 2-3 inch depth — not piled against plant stems",
            "Bed edges respected — mulch stops at the edge line, not beyond",
            "Even coverage with no bare spots or visible soil",
            "Mulch volcanoes around trees are strictly prohibited",
            "Hardscape edges clean — no mulch left on walks or drives"
        ],
        "notes": "Mulch depth must be consistent and applied professionally. 'Volcanoes' around tree trunks cause root rot and are a failed standard. Photograph depth with a ruler if questioned, and ensure walks are blown clean after application.",
        "image_url": "https://images.unsplash.com/photo-1664023304975-58b2e587d38d?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is a 'mulch volcano' and why is it unacceptable?",
        "choice_options": ["Decorative mounding — it's preferred", "Mulch piled against tree trunks — causes root rot", "A type of mulch color", "An installation technique"],
        "correct_answer": "Mulch piled against tree trunks — causes root rot",
    },
    {
        "title": "Weeding — Bed Maintenance Standard",
        "category": "Weeding",
        "division_targets": ["Maintenance"],
        "audience": "crew",
        "checklist": [
            "All visible weeds pulled from beds — root and all",
            "Weed debris removed from site, not left in beds",
            "Pre-emergent areas flagged for chemical crew follow-up",
            "Bed surface raked smooth after weeding",
            "Hardscape cracks and joints checked for weed growth"
        ],
        "notes": "Weeding is not optional — it's part of every maintenance visit. Pull weeds completely (root included). If beds have persistent weed pressure, flag for pre-emergent treatment and note it in submission.",
        "image_url": "https://images.unsplash.com/photo-1708294160695-20ece576b506?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What should you do when pulling weeds?",
        "choice_options": ["Cut at the surface", "Remove root and all", "Spray only", "Cover with mulch"],
        "correct_answer": "Remove root and all",
    },
    # ── INSTALL ──
    {
        "title": "Hardscape Installation — Paver Base & Grade",
        "category": "Hardscape",
        "division_targets": ["Install"],
        "audience": "crew",
        "checklist": [
            "Sub-base compacted in lifts — no single thick pour",
            "Screed layer is level with no voids or humps",
            "Paver pattern is consistent and joints are tight",
            "Edge restraint is installed and staked securely",
            "Final surface is swept, compacted, and polymeric sand applied"
        ],
        "notes": "Hardscape failures always trace back to base preparation. Document every layer — sub-base, screed, pavers, and edge restraint. The finished product should be level, firm underfoot, and visually consistent.",
        "image_url": "https://images.unsplash.com/photo-1761637823407-ef47925c2714?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the most common cause of hardscape failure?",
        "choice_options": ["Wrong paver color", "Improper base compaction", "Too much polymeric sand", "Weather conditions"],
        "correct_answer": "Improper base compaction",
    },
    {
        "title": "Softscape Installation — Plant Placement & Backfill",
        "category": "Softscape",
        "division_targets": ["Install"],
        "audience": "crew",
        "checklist": [
            "Root ball sits at grade — not buried or exposed",
            "Hole is 2x wider than root ball, backfilled and tamped",
            "Plants spaced per plan — no overcrowding or gaps",
            "Mulch ring applied without burying stem/trunk",
            "Water applied immediately after installation"
        ],
        "notes": "Plant installation is a long-term investment. Photograph the root ball at grade, the spacing from the plan, and the finished mulch ring. If amending soil, note the mix used in your submission.",
        "image_url": "https://images.unsplash.com/photo-1590034973922-08ef47ff7d99?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "How wide should the planting hole be relative to the root ball?",
        "choice_options": ["Same width", "1.5x wider", "2x wider", "3x wider"],
        "correct_answer": "2x wider",
    },
    {
        "title": "Landscape Lighting — Fixture Placement & Aim",
        "category": "Lighting",
        "division_targets": ["Install"],
        "audience": "crew",
        "checklist": [
            "Fixtures placed per design plan at specified heights",
            "Wiring buried at minimum 6-inch depth in conduit",
            "Connections are waterproof and accessible for service",
            "Aim tested at night — no hot spots or dark zones",
            "Transformer set to correct voltage with timer programmed"
        ],
        "notes": "Lighting must be tested at night for aim and coverage. Photograph each fixture placement during day install, then a full property shot at night showing the light spread. Wiring must be code-compliant.",
        "image_url": "https://images.unsplash.com/photo-1767054171969-b3d215ba7a64?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the minimum burial depth for landscape lighting wire?",
        "choice_options": ["2 inches", "4 inches", "6 inches", "12 inches"],
        "correct_answer": "6 inches",
    },
    {
        "title": "Drainage Installation — Grade & Flow",
        "category": "Drainage/Trenching",
        "division_targets": ["Install"],
        "audience": "crew",
        "checklist": [
            "Trench graded at minimum 1% slope toward outlet",
            "Pipe bedded in gravel with filter fabric wrap",
            "Connections sealed and tested for flow",
            "Backfill compacted in lifts — no settling voids",
            "Surface restored to match surrounding grade"
        ],
        "notes": "Drainage work is invisible once done — the photos are the only proof of quality. Document the trench grade, pipe bedding, connections, and final surface restoration. Test flow with a hose before backfill.",
        "image_url": "https://images.unsplash.com/photo-1721474932753-ad1c55bca0a0?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the minimum recommended slope for drainage pipe?",
        "choice_options": ["0.5%", "1%", "3%", "5%"],
        "correct_answer": "1%",
    },
    # ── TREE ──
    {
        "title": "Tree Pruning — ISA Standards",
        "category": "Pruning",
        "division_targets": ["Tree"],
        "audience": "crew",
        "checklist": [
            "Three-cut method used for branches over 2 inches diameter",
            "Final cut at branch collar — no flush cuts or stubs",
            "Crown thinning does not exceed 25% of live canopy",
            "All dead, diseased, and hazardous limbs removed",
            "Drop zone secured and cleared upon completion"
        ],
        "notes": "Tree work follows ISA (International Society of Arboriculture) standards. Photograph the canopy before and after, show the cut quality close-up, and document the drop zone safety setup. Never top a tree.",
        "image_url": "https://images.unsplash.com/photo-1768956737989-f170789181a9?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What method should be used for branches over 2 inches in diameter?",
        "choice_options": ["Single cut from top", "Three-cut method", "Snap and tear", "Flush cut at trunk"],
        "correct_answer": "Three-cut method",
    },
    {
        "title": "Tree Removal — Safety & Documentation",
        "category": "Tree/Plant Removal",
        "division_targets": ["Tree"],
        "audience": "crew",
        "checklist": [
            "Work zone roped off with caution tape or cones",
            "Notch cut and back cut performed correctly for directional fell",
            "Rigging used for sections near structures or utilities",
            "Stump ground to 6 inches below grade (if included)",
            "All debris chipped or removed — site left clean"
        ],
        "notes": "Tree removal is the highest-risk operation in the field. Safety documentation is non-negotiable. Photograph the work zone setup, each major cut, and the final site condition. Include PPE compliance in every photo.",
        "image_url": "https://images.unsplash.com/photo-1765064520253-379fff8eee9e?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the first step in any tree removal operation?",
        "choice_options": ["Start cutting", "Secure the work zone", "Call the client", "Check equipment fuel"],
        "correct_answer": "Secure the work zone",
    },
    # ── PLANT HEALTHCARE ──
    {
        "title": "Chemical Application — Safety & Compliance",
        "category": "Fert & Chem Treatment",
        "division_targets": ["Plant Healthcare"],
        "audience": "crew",
        "checklist": [
            "Applicator license current and on-person during application",
            "Product label read and followed — rate, timing, and method",
            "PPE worn as specified on product label",
            "Application flags placed per state regulation",
            "Wind speed below 10 mph during spray operations"
        ],
        "notes": "Chemical applications are regulated by state law. Always carry your license, follow the label exactly, and document the product, rate, and conditions. Photograph flags and any areas excluded from treatment.",
        "image_url": "https://images.unsplash.com/photo-1759922378219-1d31edb644f4?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What document must be followed exactly during chemical application?",
        "choice_options": ["Company handbook", "Product label", "Client preferences", "Weather report"],
        "correct_answer": "Product label",
    },
    # ── WINTER ──
    {
        "title": "Snow Removal — Plow & Salt Standards",
        "category": "Snow Removal",
        "division_targets": ["Winter Services"],
        "audience": "crew",
        "checklist": [
            "Plow blade set to correct height for surface type",
            "Salt applied at recommended rate — no excess",
            "Sidewalks and entryways cleared to bare pavement",
            "Snow stacked in approved locations — not blocking drainage",
            "Completion photos timestamped for liability records"
        ],
        "notes": "Snow operations are time-critical and liability-heavy. Photograph the property before, during, and after service with visible timestamps. Document salt application rates and any areas that were inaccessible.",
        "image_url": "https://images.unsplash.com/photo-1769436004760-e3a3e82993b1?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "Why must snow removal photos be timestamped?",
        "choice_options": ["For social media", "Liability records", "Client billing", "Equipment tracking"],
        "correct_answer": "Liability records",
    },
    # ── GENERAL / ALL DIVISIONS ──
    {
        "title": "Accident Prevention & Hazard Awareness",
        "category": "Safety",
        "division_targets": [],
        "audience": "crew",
        "checklist": [
            "360-degree walk-around before starting any equipment",
            "Identify overhead utilities, buried lines, and trip hazards",
            "Maintain 10-foot clearance from active roadways",
            "Use spotters when backing equipment in tight spaces",
            "Report near-misses immediately — no exceptions"
        ],
        "notes": "Safety is the foundation of every operation. Before any task begins, conduct a hazard assessment. If something feels unsafe, stop and communicate — no job is worth an injury. Report every near-miss so we can prevent the real thing.",
        "image_url": "https://images.unsplash.com/photo-1764422680743-a4dd78bc58d3?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "When should near-misses be reported?",
        "choice_options": ["Only if someone was hurt", "At the end of the week", "Immediately — no exceptions", "Only if a supervisor saw it"],
        "correct_answer": "Immediately — no exceptions",
    },
    {
        "title": "PPE Compliance — Daily Gear Check",
        "category": "Safety",
        "division_targets": [],
        "audience": "crew",
        "checklist": [
            "Safety glasses or face shield worn during all cutting/trimming operations",
            "Hearing protection worn with equipment over 85dB",
            "Steel-toe or composite-toe boots worn at all times",
            "High-visibility vest worn near roadways or active sites",
            "Gloves appropriate to the task (not one-size-fits-all)"
        ],
        "notes": "PPE is not optional. Every crew member must arrive equipped for the day's tasks. Supervisors and crew leaders are expected to enforce PPE compliance visually before work begins. Missing PPE = crew member does not work.",
        "image_url": "https://images.unsplash.com/photo-1759984738054-cbdb13ec3fda?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "At what decibel level is hearing protection required?",
        "choice_options": ["65dB", "75dB", "85dB", "95dB"],
        "correct_answer": "85dB",
    },
    {
        "title": "Photo Documentation Standard",
        "category": "Site Prep",
        "division_targets": [],
        "audience": "crew",
        "checklist": [
            "Wide establishing shot showing full work area",
            "Detail shot of primary task quality (edge, cut, paver, etc.)",
            "Street-facing or client-view shot proving finish quality",
            "Before photo if conditions warrant (damage, poor prior work)",
            "Equipment and crew visible in at least one frame"
        ],
        "notes": "Every submission must tell the story of the work. Start wide, go detail, then finish from the client's perspective. The review team cannot grade what they cannot see — clear, well-lit photos are the standard.",
        "image_url": "https://images.unsplash.com/photo-1667936102248-f4ce6e60532d?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What is the correct photo sequence for a submission?",
        "choice_options": ["Detail only", "Wide, detail, client-view", "Client-view only", "Random angles"],
        "correct_answer": "Wide, detail, client-view",
    },
    {
        "title": "Client Property Respect — Zero-Damage Protocol",
        "category": "Damage Prevention",
        "division_targets": [],
        "audience": "crew",
        "checklist": [
            "Walk the property edge before starting — note existing damage",
            "Mark sprinkler heads, invisible fences, and shallow utilities",
            "No equipment on client lawns when saturated",
            "Avoid turf ruts from mowers — change patterns weekly",
            "Report any accidental damage immediately using the damage form"
        ],
        "notes": "We operate on other people's property. Treat every yard like it's your own. Pre-existing damage should be noted before you start. If damage occurs during work, report it immediately — honesty protects the company and the client relationship.",
        "image_url": "https://images.pexels.com/photos/11400235/pexels-photo-11400235.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What should you do if you accidentally damage client property?",
        "choice_options": ["Fix it yourself", "Ignore it", "Report immediately using the damage form", "Wait until someone notices"],
        "correct_answer": "Report immediately using the damage form",
    },
    {
        "title": "Equipment Pre-Check — Daily Startup",
        "category": "Tool/Equipment Care",
        "division_targets": [],
        "audience": "crew",
        "checklist": [
            "Fluid levels checked (oil, fuel, hydraulic) before first start",
            "Blades and cutting surfaces inspected for damage or wear",
            "Safety guards and shields in place and functional",
            "Tire pressure / track tension within spec",
            "Red-tag any equipment that fails pre-check — do not operate"
        ],
        "notes": "Equipment pre-checks take 2 minutes and prevent hours of downtime. Every piece of equipment gets a visual and functional check before the first job of the day. Red-tag and report anything that fails — never operate compromised equipment.",
        "image_url": "https://images.pexels.com/photos/32208897/pexels-photo-32208897.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "training_enabled": True,
        "question_type": "multiple_choice",
        "question_prompt": "What should you do if equipment fails the pre-check?",
        "choice_options": ["Use it carefully", "Red-tag and report it", "Fix it yourself", "Use a different attachment"],
        "correct_answer": "Red-tag and report it",
    },
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # 1. Remove TEST entries
    result = await db.standards_library.delete_many({"title": {"$regex": "^TEST"}})
    print(f"Deleted {result.deleted_count} TEST entries")

    # 2. Remove old placeholder standards (from initial seed)
    old_titles = ["Clean bed edge finish", "Cleanup completion proof", "Mulch bed cleanliness", "Tree pruning clarity"]
    result2 = await db.standards_library.delete_many({"title": {"$in": old_titles}})
    print(f"Deleted {result2.deleted_count} old placeholder entries")

    # 3. Insert new industry standards
    for s in STANDARDS:
        existing = await db.standards_library.find_one({"title": s["title"]}, {"_id": 0})
        if existing:
            print(f"  Skipping (exists): {s['title']}")
            continue
        doc = {
            "id": make_id("std"),
            "title": s["title"],
            "category": s["category"],
            "audience": s.get("audience", "crew"),
            "division_targets": s.get("division_targets", []),
            "checklist": s.get("checklist", []),
            "notes": s.get("notes", ""),
            "owner_notes": "",
            "shoutout": "",
            "image_url": s.get("image_url", ""),
            "training_enabled": s.get("training_enabled", True),
            "question_type": s.get("question_type", "multiple_choice"),
            "question_prompt": s.get("question_prompt", ""),
            "choice_options": s.get("choice_options", []),
            "correct_answer": s.get("correct_answer", ""),
            "is_active": True,
            "search_text": " ".join([
                s["title"].lower(),
                s["category"].lower(),
                s.get("notes", "").lower(),
                " ".join(d.lower() for d in s.get("division_targets", [])),
            ]),
            "created_by": "system_seed",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.standards_library.insert_one(doc)
        print(f"  Inserted: {s['title']}")

    # 4. Update demo crew with leader_name
    await db.crew_access_links.update_one(
        {"code": "bb01032c"},
        {"$set": {"leader_name": "Alejandro Ruiz-Domian"}},
    )
    print("Updated demo crew 'Install Alpha' with leader_name='Alejandro Ruiz-Domian'")

    total = await db.standards_library.count_documents({})
    print(f"\nTotal standards in library: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

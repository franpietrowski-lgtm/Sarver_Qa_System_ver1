import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

import shared.deps as deps
from shared.deps import storage_is_configured, get_supabase_client
from shared.seed_data import seed_defaults

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
from routes.crew_members import router as crew_members_router
from routes.team_profiles import router as team_profiles_router
from routes.pdf_exports import router as pdf_exports_router
from routes.onboarding import router as onboarding_router
from routes.coaching_loop import router as coaching_loop_router
from routes.incidents import router as incidents_router
from routes.crew_assignments import router as crew_assignments_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("server")


def get_fresh_db():
    c = AsyncIOMotorClient(mongo_url)
    return c, c[db_name]


client, db = get_fresh_db()
deps.db = db

app = FastAPI(title="Field Quality Capture & Review System")
api_router = APIRouter(prefix="/api")


# ── Startup ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    global client, db
    try:
        await db.command("ping")
    except Exception:
        client, db = get_fresh_db()
        deps.db = db

    await seed_defaults(db)

    # Indexes
    await db.rapid_reviews.create_index("submission_id", unique=True)
    await db.rapid_review_sessions.create_index("reviewer_id")
    await db.rapid_review_sessions.create_index("created_at")
    await db.standards_library.create_index("id", unique=True)
    await db.training_sessions.create_index("code", unique=True)

    # Auto-delete archived QRs older than 30 days
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    deleted = await db.crew_access_links.delete_many({"archived": True, "archived_at": {"$lt": cutoff}})
    if deleted.deleted_count:
        logger.info("Auto-deleted %d archived crew QR links (>30 days)", deleted.deleted_count)

    if storage_is_configured():
        try:
            get_supabase_client()
            logger.info("Supabase storage client initialized")
        except Exception as exc:
            logger.error("Supabase storage initialization failed: %s", exc)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ── Route registration ──────────────────────────────────────────────────

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
api_router.include_router(crew_members_router)
api_router.include_router(team_profiles_router)
api_router.include_router(pdf_exports_router)
api_router.include_router(onboarding_router)
api_router.include_router(coaching_loop_router)
api_router.include_router(incidents_router)
api_router.include_router(crew_assignments_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

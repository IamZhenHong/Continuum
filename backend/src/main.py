from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from src.config.settings import settings
from src.utils.redis_helper import redis_client
from src.routers.auth import router as auth_router
# ✅ Initialize Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
import os

# Enable insecure transport for OAuth (only for local dev)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# ✅ Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hyperflow AI Assistant API for managing learning resources.",
    docs_url="/docs",  # Swagger UI endpoint
    redoc_url="/redoc",  # ReDoc UI endpoint
    openapi_url="/openapi.json"  # OpenAPI schema
)

# ✅ CORS Configuration (Allow only trusted origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])  # Include Auth Router

# ✅ Root Endpoint
@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API!", "version": settings.APP_VERSION}


# ✅ Startup Event (System Initialization)
@app.on_event("startup")
async def startup_event():
    logging.info(f"🚀 {settings.APP_NAME} is starting...")
    logging.info(f"🌍 Environment: {settings.ENV}")

    # ✅ Verify External Services Connectivity (Redis, Supabase, etc.)
    try:
        from src.utils.redis_helper import redis_client
        redis_client.ping()  # Check Redis Connection
        logging.info("✅ Redis connection established.")
    except Exception as e:
        logging.error(f"❌ Redis connection failed: {e}")

    try:
        from src.config.settings import supabase_client
        response = supabase_client.auth.sign_out()
        logging.info("✅ Supabase connected.")
    except Exception as e:
        logging.error(f"❌ Supabase connection failed: {e}")


    try:
        from bot.bot_runner import start_bot
        asyncio.create_task(start_bot())
        logging.info("✅ Telegram bot started.")
    except Exception as e:
        logging.error(f"❌ Telegram bot failed to start: {e}")

    # try:
    #     asyncio.create_task(run_queue_processing())
    #     logging.info("✅ Queue processing started.")
    # except Exception as e:
    #     logging.error(f"❌ Queue processing failed to start: {e}")

    logging.info("📡 All external services checked.")


# ✅ Shutdown Event (Cleanup Tasks)
@app.on_event("shutdown")
async def shutdown_event():
    logging.info(f"🛑 {settings.APP_NAME} is shutting down...")

    # ✅ Perform Cleanup if Needed (Close DB Connections, Flush Queues, etc.)
    try:
        redis_client.close()
        logging.info("✅ Redis connection closed.")
    except Exception as e:
        logging.warning(f"⚠️ Error closing Redis: {e}")

    logging.info("🔒 API shutdown complete.")

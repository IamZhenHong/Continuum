from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.routers import messages, processing, intent_router, summarisation
import logging

# ✅ Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hyperflow AI Assistant API for managing learning resources."
)

# ✅ Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include API Routers
app.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(processing.router, prefix="/processing", tags=["Processing"])
app.include_router(intent_router.router, prefix="/intent", tags=["Intent"])
app.include_router(summarisation.router, prefix="/summarise", tags=["Summarisation"])

# ✅ Root Endpoint
@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API!"}

# ✅ Startup Event (Optional: Logging, DB Checks, etc.)
@app.on_event("startup")
async def startup_event():
    logging.info(f"🚀 {settings.APP_NAME} is starting...")
    logging.info(f"🌍 Environment: {settings.ENV}")

# ✅ Shutdown Event
@app.on_event("shutdown")
async def shutdown_event():
    logging.info(f"🛑 {settings.APP_NAME} is shutting down...")

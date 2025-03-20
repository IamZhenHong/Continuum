import time
import logging
from fastapi import APIRouter, BackgroundTasks
from src.config.settings import settings, redis_client, supabase_client
import asyncio
from src import schemas
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from src.services.enrichment_engine.engine import enrich
import traceback

# ✅ Initialize Router
router = APIRouter()

import asyncio
import logging


from celery import shared_task

@shared_task
def process_resource(resource_id: int, user_id: int, message: str):
    """Processes a resource asynchronously using Celery"""
    try:
        logging.info(f"🚀 Processing Resource ID: {resource_id} (User ID: {user_id})")

        # ✅ Track in Redis
        redis_client.incr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "processing")

        logging.info(f"🧠 Running AI enrichment for resource {resource_id}...")

        # ✅ Call Enrichment Engine
        response = enrich(schemas.EnrichResourceRequest(resource_id=resource_id, message=message, user_id=user_id))

        if not response:
            raise Exception("❌ Enrichment failed")

        # ✅ Update Supabase - Mark as processed
        supabase_client.table("resources").update({"is_processed": True}).eq("id", resource_id).execute()

        # ✅ Update Redis
        redis_client.decr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "completed")

        # ✅ Mark processing as completed in Supabase
        update_response = (
            supabase_client.table("processing_queue")
            .update({"status": "completed", "completed_at": "now()"})
            .eq("resource_id", resource_id)
            .execute()
        )

        if update_response.data:
            logging.info(f"✅ Processing complete for Resource ID: {resource_id}")
        else:
            logging.error(f"❌ Supabase update failed for Resource ID: {resource_id}")

        # ✅ Reset Redis queue flag if no pending jobs
        remaining_jobs = int(redis_client.get(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT) or 0)
        if remaining_jobs <= 0:
            redis_client.delete("queue:has_pending")
            logging.info("✅ No more pending jobs. Redis queue flag reset.")

    except Exception as e:
        logging.error(f"❌ ERROR in processing Resource ID {resource_id}: {str(e)}")
        logging.error(traceback.format_exc())  # Print full error trace

def start_processing():
    """
    Fetches multiple pending jobs from the processing queue and starts processing using Celery.

    - Selects the highest-priority pending resources.
    - Updates status to "processing" in Supabase.
    - Sends tasks to Celery for parallel execution.
    """
    logging.info("🛠️ Checking for pending jobs in the database...")

    # ✅ Fetch Multiple Pending Jobs
    jobs = (
        supabase_client.table("processing_queue")
        .select("resource_id, user_id")
        .eq("status", "pending")
        .order("priority", desc=True)
        .limit(3)
        .execute()
    )

    if not jobs.data:
        logging.info("✅ No pending jobs found. Resetting Redis flag.")
        redis_client.delete("queue:has_pending")  # ✅ Reset flag
        return {"message": "No pending jobs"}

    # ✅ Start Processing Each Job
    for job in jobs.data:
        resource_id, user_id = job["resource_id"], job["user_id"]

        # ✅ Mark as "processing" in Supabase
        supabase_client.table("processing_queue").update(
            {"status": "processing", "started_at": "now()"}
        ).eq("resource_id", resource_id).execute()

        # ✅ Get Message Content
        message_id = (
            supabase_client.table("resources")
            .select("message_id")
            .eq("id", resource_id)
            .execute()
        )

        message = (
            supabase_client.table("messages")
            .select("message")
            .eq("id", message_id.data[0]["message_id"])
            .execute()
        )

        logging.info(f"🚀 Sending task to Celery for Resource ID: {resource_id}")

        # ✅ Send Task to Celery
        process_resource.delay(resource_id, user_id, message.data[0]["message"])

    return {"message": f"Processing started for {len(jobs.data)} resources"}


import time

def run_queue_processing():
    """Continuously checks Redis for pending jobs and triggers processing."""
    logging.info("🔄 Queue processing loop started...")

    while True:
        has_pending = redis_client.get("queue:has_pending")

        logging.info(f"🛠️ Redis Queue Status: {has_pending}")  # ✅ Debug log

        if has_pending == "1":
            logging.info("🛠️ Redis detected pending jobs. Processing...")
            start_processing()  # ✅ Now uses Celery

        time.sleep(3)  # ✅ Check every 3 seconds


async def add_to_processing_queue(data: schemas.AddToProcessingQueueRequest):
    """Adds a new resource to the processing queue."""
    insert_response = (
        supabase_client.table("processing_queue")
        .insert(
            {
                "user_id": data.user_id,
                "resource_id": data.resource_id,
                "status": "pending",
                "priority": 1,  # Default priority
            }
        )
        .execute()
    )

    print("Adding to processing queue")

    redis_client.set("queue:has_pending", "1")  # Mark pending jobs in Redis

    if insert_response.data:
        logging.info(f"✅ Added Resource ID {data.resource_id} to processing queue")
    else:
        logging.error(
            f"❌ Error adding Resource ID {data.resource_id} to processing queue"
        )

    return insert_response.data

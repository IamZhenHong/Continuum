import logging
import traceback
from celery import shared_task
from src.config.settings import settings, redis_client, supabase_client
from src.services.enrichment_engine.engine import enrich
from src import schemas
import asyncio

import time
import logging
from celery import shared_task
from src.config.settings import supabase_client, redis_client
from bot.telegram_interface import send_telegram_message

logger = logging.getLogger(__name__)

@shared_task
def process_resource_task(resource_id: int, user_id: int):
    """
    Legacy/alternative background task to simulate resource processing.
    """
    logger.info(f"🚀 [Simulate] Processing Resource ID {resource_id} for User {user_id}")

    time.sleep(10)  # Simulated delay — replace with actual logic

    logger.info(f"✅ [Simulate] Marking Resource ID {resource_id} as completed")
    supabase_client.table("processing_queue").update(
        {"status": "completed"}
    ).eq("resource_id", resource_id).execute()

    logger.info(f"✅ [Simulate] Done processing Resource ID {resource_id}")
    return f"Resource {resource_id} processed successfully!"


@shared_task(name="process_resource")
def process_resource(resource_id: int, user_id: int, message: str):
    """
    Primary enrichment task triggered by dispatcher.
    """
    try:
        logging.info(f"🚀 Starting Enrichment for Resource ID: {resource_id} (User ID: {user_id})")

        # Update Redis processing state
        redis_client.incr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "processing")

        # Log payload
        logging.info("📦 Enrichment Input Payload:")
        logging.info(f"   • resource_id: {resource_id}")
        logging.info(f"   • user_id: {user_id}")
        logging.info(f"   • message: {message}")

        # Create enrichment schema payload
        request_payload = schemas.EnrichResourceRequest(
            resource_id=resource_id,
            message=message,
            user_id=user_id
        )

        # Call enrichment engine
        logging.info("🧠 Invoking enrichment engine...")
        response = enrich(request_payload)
        logging.info(f"🧠 Enrichment engine responded with: {response}")

        if not response:
            raise Exception("❌ Enrichment failed — response was empty or invalid.")

        # Update Supabase flags
        logging.info("📍 Marking resource as processed in Supabase...")
        supabase_client.table("resources").update({"is_processed": True}).eq("id", resource_id).execute()
        supabase_client.table("processing_queue").update({
            "status": "completed", "completed_at": "now()"
        }).eq("resource_id", resource_id).execute()

        # Update Redis
        redis_client.decr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "completed")

        redis_client.set(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT, 0)

        # Cleanup flag if all jobs done
        if int(redis_client.get(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT) or 0) <= 0:
            logging.info("🧹 No active jobs remaining. Clearing pending flag...")
            redis_client.delete("queue:has_pending")

        logging.info(f"✅ Resource {resource_id} fully processed for User {user_id}")

    except Exception as e:
        logging.error(f"❌ ERROR during enrichment of Resource {resource_id}: {e}")
        logging.error(traceback.format_exc())


@shared_task(name="check_and_dispatch")
def run_queue_dispatcher():
    """
    Periodic task triggered by Celery Beat to dispatch jobs from queue.
    """
    logging.info("📣 Dispatcher triggered — checking queue...")
    from src.services.processing_tasks import start_processing
    start_processing()


import logging
from src.config.settings import supabase_client, redis_client
from src.services.processing_tasks import process_resource
from src import schemas
from src.config.settings import supabase_client, redis_client
from celery import shared_task
from src.services.processing_tasks import process_resource

def start_processing():
    logging.info("🛠️ Checking for pending jobs in queue...")

    # Step 1: Query for pending jobs
    jobs = supabase_client.table("processing_queue").select("resource_id, user_id") \
        .eq("status", "pending") \
        .order("priority", desc=True) \
        .limit(3) \
        .execute()

    logging.info(f"📋 Found {len(jobs.data)} pending job(s)")

    if not jobs.data:
        logging.info("📭 No pending jobs found. Clearing Redis flag.")
        redis_client.delete("queue:has_pending")
        return

    logging.info(f"📋 Found {len(jobs.data)} pending job(s)")

    for job in jobs.data:
        resource_id = job["resource_id"]
        user_id = job["user_id"]
        logging.info(f"🧩 Preparing to process Resource ID: {resource_id}, User ID: {user_id}")

        # Step 2: Update queue status
        logging.info(f"🔄 Marking Resource ID {resource_id} as 'processing'")
        supabase_client.table("processing_queue").update({
            "status": "processing",
            "started_at": "now()"
        }).eq("resource_id", resource_id).execute()

        # Step 3: Retrieve associated message
        logging.info(f"📩 Fetching message ID for Resource ID {resource_id}")
        message_id_result = supabase_client.table("resources").select("message_id").eq("id", resource_id).execute()
        message_id = message_id_result.data[0]["message_id"]

        logging.info(f"📝 Fetching message content for Message ID {message_id}")
        message_result = supabase_client.table("messages").select("message").eq("id", message_id).execute()
        message = message_result.data[0]["message"]

        # Step 4: Dispatch task to Celery
        logging.info(f"🚀 Dispatching Resource ID {resource_id} to Celery for processing")
        process_resource.delay(resource_id, user_id, message)


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
        send_telegram_message(
            data.user_id,
            f"""✅ Added to your queue! I’ll send you the distilled goodness once it’s ready. 🚀"""
        )

    else:
        logging.error(
            f"❌ Error adding Resource ID {data.resource_id} to processing queue"
        )

    return insert_response.data

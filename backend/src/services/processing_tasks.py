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
    Background task to process resources.
    """
    logger.info(f"🚀 Processing Resource ID {resource_id} for User {user_id}")

    # ✅ Simulate processing delay (Replace with actual enrichment logic)
    time.sleep(10)

    # ✅ Mark the resource as completed in Supabase
    supabase_client.table("processing_queue").update(
        {"status": "completed"}
    ).eq("resource_id", resource_id).execute()

    logger.info(f"✅ Processing complete for Resource ID: {resource_id}")
    return f"Resource {resource_id} processed successfully!"


@shared_task(name="process_resource")
def process_resource(resource_id: int, user_id: int, message: str):
    try:
        logging.info(f"🚀 Processing Resource ID: {resource_id} (User ID: {user_id})")

        redis_client.incr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "processing")

        logging.info("📦 Calling enrichment engine with data:")
        logging.info(f"   • resource_id: {resource_id}")
        logging.info(f"   • user_id: {user_id}")
        logging.info(f"   • message: {message}")

        request_payload = schemas.EnrichResourceRequest(
            resource_id=resource_id,
            message=message,
            user_id=user_id
        )

        response = enrich(request_payload)

        logging.info(f"🧠 Enrichment response: {response}")

        if not response:
            raise Exception("❌ Enrichment failed — received empty response.")

        supabase_client.table("resources").update({"is_processed": True}).eq("id", resource_id).execute()
        supabase_client.table("processing_queue").update({
            "status": "completed", "completed_at": "now()"
        }).eq("resource_id", resource_id).execute()

        redis_client.decr(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT)
        redis_client.set(f"{settings.REDIS.REDIS_RESOURCE_STATUS_PREFIX}{user_id}", "completed")

        if int(redis_client.get(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT) or 0) <= 0:
            redis_client.delete("queue:has_pending")

        logging.info(f"✅ Finished Resource ID: {resource_id}")

    except Exception as e:
        logging.error(f"❌ ERROR in process_resource: {e}")
        logging.error(traceback.format_exc())

@shared_task(name="check_and_dispatch")
def run_queue_dispatcher():
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
    logging.info("🛠️ Checking for pending jobs...")
    jobs = supabase_client.table("processing_queue").select("resource_id, user_id") \
        .eq("status", "pending") \
        .order("priority", desc=True).limit(3).execute()

    if not jobs.data:
        redis_client.delete("queue:has_pending")
        return

    for job in jobs.data:
        resource_id = job["resource_id"]
        user_id = job["user_id"]

        supabase_client.table("processing_queue").update({
            "status": "processing",
            "started_at": "now()"
        }).eq("resource_id", resource_id).execute()

        message_id = supabase_client.table("resources").select("message_id").eq("id", resource_id).execute()
        message = supabase_client.table("messages").select("message").eq("id", message_id.data[0]["message_id"]).execute()

        logging.info(f"🚀 Dispatching Resource ID {resource_id} to Celery")
        process_resource.delay(resource_id, user_id, message.data[0]["message"])

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

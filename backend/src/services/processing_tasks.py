import logging
import traceback
from celery import shared_task
from src.config.settings import settings, redis_client, supabase_client
from src.services.enrichment_engine.engine import enrich
from src import schemas
import asyncio

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

@shared_task(name="queue.check_and_dispatch")
def run_queue_dispatcher():
    from src.queue.dispatch import start_processing
    start_processing()

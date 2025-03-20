import time
import logging
from celery import shared_task
from src.config.settings import supabase_client, redis_client

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

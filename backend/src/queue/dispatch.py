import logging
from src.config.settings import supabase_client, redis_client
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




# ✅ Processing Queue (Redis + Supabase)
async def process_resource(resource_id, user_id):
    redis_client.incr("queue:processing_count")
    redis_client.set(f"resource:status:{user_id}", "processing")

    time.sleep(30)  # Simulated processing

    redis_client.decr("queue:processing_count")
    redis_client.set(f"resource:status:{user_id}", "completed")

    supabase.table("resource_queue").update({"status": "completed"}).eq("resource_id", resource_id).execute()

# ✅ Start processing queue
@app.post("/start_processing")
async def start_processing(background_tasks: BackgroundTasks):
    job = supabase.table("resource_queue").select("resource_id, user_id").eq("status", "pending").order("priority", desc=True).limit(1).execute().data
    if not job:
        return {"message": "No pending jobs"}

    resource_id, user_id = job[0]["resource_id"], job[0]["user_id"]
    supabase.table("resource_queue").update({"status": "processing"}).eq("resource_id", resource_id).execute()

    background_tasks.add_task(process_resource, resource_id, user_id)
    return {"message": "Processing started", "resource_id": resource_id}

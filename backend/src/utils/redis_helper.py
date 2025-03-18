import redis
from src.config.settings import settings

# ✅ Initialize Redis Client
redis_client = redis.StrictRedis.from_url(settings.REDIS.REDIS_URL, decode_responses=True)


# ✅ Queue Management Functions
def add_to_queue(resource_id: int, user_id: int):
    """
    Adds a resource to the processing queue.
    """
    redis_client.rpush("processing_queue", resource_id)
    redis_client.set(f"resource:status:{user_id}", "pending")
    update_estimated_time()


def remove_from_queue(resource_id: int, user_id: int):
    """
    Removes a resource from the processing queue after it's processed.
    """
    redis_client.lrem("processing_queue", 1, resource_id)
    redis_client.set(f"resource:status:{user_id}", "completed")
    update_estimated_time()


def update_estimated_time():
    """
    Estimates remaining processing time based on queue length.
    """
    pending_jobs = redis_client.llen("processing_queue")
    estimated_time = pending_jobs * settings.PROCESSING_TIME_ESTIMATE
    redis_client.set("queue:estimated_time", estimated_time)


def get_queue_status():
    """
    Returns real-time queue status.
    """
    pending_count = redis_client.llen("processing_queue")
    processing_count = int(redis_client.get("queue:processing_count") or 0)
    estimated_time = redis_client.get("queue:estimated_time") or "Unknown"

    return {
        "pending": pending_count,
        "processing": processing_count,
        "estimated_time": estimated_time
    }


def increment_processing():
    """
    Increments the number of processing jobs.
    """
    redis_client.incr("queue:processing_count")
    update_estimated_time()


def decrement_processing():
    """
    Decrements the number of processing jobs.
    """
    redis_client.decr("queue:processing_count")
    update_estimated_time()


def set_resource_status(user_id: int, status: str):
    """
    Sets the processing status for a user's resource.
    """
    redis_client.set(f"resource:status:{user_id}", status)


def get_resource_status(user_id: int):
    """
    Gets the processing status for a user's resource.
    """
    return redis_client.get(f"resource:status:{user_id}") or "Unknown"


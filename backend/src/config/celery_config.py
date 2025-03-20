from celery import Celery
from src.config.settings import settings

# ✅ Initialize Celery
celery_app = Celery(
    "worker",
    broker=settings.REDIS.REDIS_URL,  # ✅ Use Redis as the message broker
    backend=settings.REDIS.REDIS_URL,  # ✅ Store results in Redis
)

# ✅ Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

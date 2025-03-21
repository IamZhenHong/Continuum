from celery import Celery
from src.config.settings import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS.REDIS_URL,
    backend=settings.REDIS.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# ✅ Auto-discover tasks
celery_app.autodiscover_tasks(["src.services"])

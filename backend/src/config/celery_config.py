from celery import Celery
from src.config.settings import settings
import src.services.processing_tasks
import src.services.notifications

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
celery_app.autodiscover_tasks([
    "src.services",
    "src.queue",  # wherever you keep tasks

])

from celery.schedules import crontab
from src.config.celery_config import celery_app

celery_app.conf.beat_schedule = {
    "check-processing-queue-every-5s": {
        "task": "queue.check_and_dispatch",
        "schedule": 5.0,  # Every 5 seconds
    },
    # "send-learning-digest-daily": {
    #     "task": "notifications.send_daily_learning_digest",
    #     "schedule": 5.0,  # Every 5 seconds
    # },
    "send-weekly-summary": {
        "task": "notifications.send_weekly_summary",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
    },
}



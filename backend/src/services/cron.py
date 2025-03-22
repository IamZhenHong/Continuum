# src/tasks/cron.py
from celery import shared_task
from bot.telegram_interface import send_telegram_message
from src.config.settings import supabase_client
import logging

@shared_task
def send_daily_learning():
    logging.info("📩 Sending daily learning summary...")

    users = supabase_client.table("users").select("id").execute().data
    for user in users:
        # You can fetch relevant enriched resources here
        send_telegram_message(user["id"], "🌟 Here's your daily learning insight!")

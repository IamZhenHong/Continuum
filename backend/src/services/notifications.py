# src/services/notifications.py
from celery import shared_task
from src.config.settings import supabase_client
from bot.telegram_interface import send_telegram_message

@shared_task(name="notifications.send_daily_learning_digest")
def send_daily_learning_digest():
    users = supabase_client.table("users").select("id").execute().data
    for user in users:
        send_telegram_message(user["id"], "📚 Here's your daily learning digest!")

# @shared_task(name="notifications.send_weekly_recap")
# def send_weekly_recap(name="notifications.send_weekly_recap"):
#     users = supabase_client.table("users").select("id").execute().data
#     for user in users:
#         supabase_client.table("ai_enrichments").select("id").execute()

#         send_telegram_message(user["id"], "📅 Here's your weekly recap!")
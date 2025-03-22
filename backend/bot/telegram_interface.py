from typing import Optional
import requests
import logging
from src.config.settings import supabase_client
from src.config.settings import settings
from pydantic import BaseModel
from telegram import BotCommand

TELEGRAM_API_URL = settings.TELEGRAM.TELEGRAM_API_URL

# ✅ Send Message to User (Callable by Other Routers)
def send_telegram_message(user_id: int, message: str):
    """Send a message to a user via Telegram bot."""
    print("📤 Sending Message to User:", user_id, message)

    user = supabase_client.table("users").select("telegram_id").eq("id", user_id).execute()
    print(user)
    user_telegram_id = user.data[0]["telegram_id"] if user.data else None
    payload = {
        "chat_id": user_telegram_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(TELEGRAM_API_URL, json=payload)
        if response.status_code == 200:
            logging.info(f"✅ Message sent to {user_id}: {message}")
            return response.json()
        else:
            logging.error(f"❌ Failed to send message: {response.json()}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"🚨 Telegram API Request Error: {e}")
        return None
    
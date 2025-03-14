import logging
import requests
import asyncio
from fastapi import APIRouter, BackgroundTasks
from src.config.settings import settings
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

router = APIRouter()







TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7619287685:AAGwEGyTnv2yyb6P5yWEh4XbDvJCr1MSQRQ")

logging.basicConfig(level=logging.INFO)

# ✅ Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! Send me a message or link, and I'll save it.")

# ✅ Handle Text & Links
import requests
import json

# ✅ Handle Text & Links
async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    user_id = update.message.from_user.id

    payload = {
        "user_id": user_id,
        "message": message_text,
        "message_type": "link" if "http" in message_text else "text"
    }

    print("📩 Payload Sent:", payload)

    try:
        # ✅ Single API Call (store_message now triggers intent processing)
        response = requests.post(f"{BASE_URL}/store_message", json=payload)
        response_json = response.json() if response.status_code == 200 else None

        if response.status_code == 200:
            intent_result = response_json.get("intent", {})
            # await update.message.reply_text(f"✅ Processed Successfully:\n{intent_result}")
        else:
            await update.message.reply_text("❌ Error processing message.")

    except requests.exceptions.RequestException as e:
        print("🚨 API Request Error:", str(e))
        await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")


# ✅ Handle Images
async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    file_id = update.message.photo[-1].file_id

    payload = {
        "user_id": user_id,
        "message": file_id,
        "message_type": "image"
    }

    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        await update.message.reply_text("Image saved successfully!")
    else:
        await update.message.reply_text("Error saving image.")

def send_telegram_message(user_id: int, message: str):
    """Send a message to a user via Telegram bot (without predefined URL)."""
    
    payload = {
        "chat_id": user_id,
        "text": message,
        "parse_mode": "Markdown"  # Supports bold, italic, etc.
    }

    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=payload
    )
    
    if response.status_code == 200:
        print(f"✅ Message sent to {user_id}: {message}")
        return response.json()
    else:
        print(f"❌ Failed to send message: {response.json()}")
        return None

async def queue_status(update: Update, context: CallbackContext):
    pending_count = redis_client.llen("resource_queue")
    processing_count = redis_client.llen("processing_count") or 0
    await update.message.reply_text(f"📊 Queue Status:\nPending: {pending_count}\nProcessing: {processing_count}")

# ✅ Setup Bot
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("queue", queue_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

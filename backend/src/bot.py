import logging
import requests
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.config.settings import settings
from src.utils.redis_helper import redis_client
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from src.config.settings import supabase_client
# ✅ Initialize Router
router = APIRouter()

# ✅ Load Telegram Settings
TELEGRAM_BOT_TOKEN = settings.TELEGRAM.TELEGRAM_BOT_TOKEN.get_secret_value()
TELEGRAM_API_URL = settings.TELEGRAM.TELEGRAM_API_URL
BASE_URL = settings.APP_BASE_URL

# ✅ Initialize Telegram Bot
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# ✅ Logging Configuration
logging.basicConfig(level=logging.INFO)


# ✅ /start Command
async def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    await update.message.reply_text("Hello! Send me a message or link, and I'll process it.")


# ✅ Handle Incoming Text Messages
import httpx  # Use async HTTP client

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
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/messages/store_message", json=payload)
        
        if response.status_code == 200:
            response_json = response.json()
            intent_result = response_json.get("intent", "No intent detected")
            await update.message.reply_text(f"✅ Processed Successfully:\n{intent_result}")
        else:
            await update.message.reply_text("❌ Error processing message.")
    
    except httpx.HTTPError as e:
        print("🚨 API Request Error:", str(e))
        await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")


# # ✅ Handle Images
# async def handle_photo(update: Update, context: CallbackContext):
#     """Handles images sent by users and routes them to FastAPI."""
#     user_id = update.message.from_user.id
#     file_id = update.message.photo[-1].file_id

#     payload = {
#         "user_id": user_id,
#         "message": file_id,
#         "message_type": "image"
#     }

#     try:
#         response = requests.post(f"{BASE_URL}/messages/store", json=payload)
#         if response.status_code == 200:
#             await update.message.reply_text("📷 Image saved successfully!")
#         else:
#             await update.message.reply_text("❌ Error saving image.")
#     except requests.exceptions.RequestException as e:
#         logging.error(f"🚨 API Request Error: {e}")
#         await update.message.reply_text("⚠️ Failed to reach backend service.")


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


# ✅ Check Processing Queue Status
async def queue_status(update: Update, context: CallbackContext):
    """Checks queue status from Redis and sends an update to the user."""
    pending_count = redis_client.llen("resource_queue")
    processing_count = redis_client.get("queue:processing_count") or 0
    estimated_time = redis_client.get("queue:estimated_time") or "Unknown"

    message = (
        f"📊 **Queue Status:**\n"
        f"🔄 Pending: {pending_count}\n"
        f"⚙️ Processing: {processing_count}\n"
        f"⏳ Estimated Completion Time: {estimated_time} seconds"
    )

    await update.message.reply_text(message)


# ✅ Register Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("queue", queue_status))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
# telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# ✅ Background Task to Start Telegram Bot
async def run_telegram_bot():
    """Runs the Telegram bot inside an asyncio event loop."""
    logging.info("🚀 Starting Telegram bot...")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES,poll_interval = 5)

# ✅ FastAPI Endpoint: Start Telegram Bot
# ✅ Background Task to Start Telegram Bot
async def start_bot():
    """Manually start the Telegram bot if it stops."""
    asyncio.create_task(run_telegram_bot())
    return {"message": "Telegram bot started!"}

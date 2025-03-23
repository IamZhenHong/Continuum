
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from src.config.settings import supabase_client
from src.utils.redis_helper import redis_client
from src.config import settings
import logging
from src.utils.redis_helper import redis_client
from src.config import settings

# ✅ /start Command
async def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    await update.message.reply_text("Hello! Send me a message or link, and I'll process it.")


# ✅ Check Processing Queue Status
async def queue_status(update: Update, context: CallbackContext):
    """Checks queue status from Redis and sends an update to the user."""
    try:
        logging.info("🔍 Checking queue status...")

        # Debug: Print all relevant Redis keys
        logging.debug("🔧 Fetching Redis keys for status...")

        # Check if the Redis settings are defined
        if not hasattr(settings.settings.REDIS, 'REDIS_QUEUE_PROCESSING_COUNT'):
            raise ValueError("REDIS_QUEUE_PROCESSING_COUNT setting is missing in the configuration.")
        # if not hasattr(settings, 'PROCESSING_TIME_ESTIMATE'):
        #     raise ValueError("PROCESSING_TIME_ESTIMATE setting is missing.")

        # Fetch from Redis
        queue_key = "resource_queue"
        processing_key = settings.settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT
        estimate_key = settings.settings.PROCESSING_TIME_ESTIMATE

        logging.debug(f"📦 Queue key: {queue_key}")
        logging.debug(f"⚙️ Processing count key: {processing_key}")
        # logging.debug(f"⏳ Estimate key: {estimate_key}")

        pending_count = redis_client.llen(queue_key)
        processing_count = redis_client.get(processing_key)
        estimated_time = redis_client.get(estimate_key)

        # Safe fallback handling
        processing_count = int(processing_count or 0)
        estimated_time = int(estimated_time or 0)

        logging.info(f"📊 Redis Stats → Pending: {pending_count}, Processing: {processing_count}, Estimate: {estimated_time}s")

        message = (
            f"📊 *Queue Status:*\n"
            f"🔄 *Pending:* {pending_count}\n"
            f"⚙️ *Processing:* {processing_count}\n"
            # f"⏳ *Estimated Completion Time:* {estimated_time} seconds"
        )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logging.exception("❌ Error while checking queue status")
        await update.message.reply_text(f"❌ Error fetching queue status: {str(e)}")



async def show_latest_processed_resources_list(update: Update, context: CallbackContext):
    """Shows the latest processed resources that the user has not yet viewed."""
    user_telegram_id = update.message.from_user.id  # Get the Telegram user ID
    
    user_id = supabase_client.table("users") \
        .select("id") \
        .eq("telegram_id", user_telegram_id) \
        .execute() \
        .data[0]["id"]
    
    # ✅ Fetch latest processed resources where is_completed = True and the user has not viewed them
    resources = supabase_client.table("resources") \
        .select("id, title, url, is_processed") \
        .eq("is_processed", True) \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()
    
    print("📋 Latest Processed Resources:", resources.data)
    
    if not resources.data:
        await update.message.reply_text("✅ No new processed resources. You're all caught up!")
        return

    keyboard = [
    [InlineKeyboardButton(resource.get("title") or "Untitled Resource", callback_data=f"view_resource_{resource['id']}")]
    for resource in resources.data
]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 **Select a resource to view:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from src.config.settings import supabase_client
from src.utils.redis_helper import redis_client
from src.config import settings

# ✅ /start Command
async def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    await update.message.reply_text("Hello! Send me a message or link, and I'll process it.")


# ✅ Check Processing Queue Status
async def queue_status(update: Update, context: CallbackContext):
    """Checks queue status from Redis and sends an update to the user."""
    pending_count = redis_client.llen("resource_queue")
    processing_count = redis_client.get(settings.REDIS.REDIS_QUEUE_PROCESSING_COUNT) or 0
    estimated_time = redis_client.get(settings.PROCESSING_TIME_ESTIMATE) or "Unknown"

    message = (
        f"📊 **Queue Status:**\n"
        f"🔄 Pending: {pending_count}\n"
        f"⚙️ Processing: {processing_count}\n"
        f"⏳ Estimated Completion Time: {estimated_time} seconds"
    )

    await update.message.reply_text(message)

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

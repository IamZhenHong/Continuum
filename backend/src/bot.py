import logging
import requests
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.config.settings import settings
from src.utils.redis_helper import redis_client
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from src.config.settings import supabase_client
import httpx  # Use async HTTP client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from src.services.generate_pdf import generate_pdf, upload_pdf_to_supabase, save_pdf_locally

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


# ✅ Function to Set Telegram Bot Commands
async def set_telegram_commands():
    """Registers bot commands for Telegram (ensures they show in the chat)."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("queue_status", "Show processing queue status"),
        BotCommand("latest_resources", "Show latest processed resources")
    ]
    await telegram_app.bot.set_my_commands(commands)
    logging.info("✅ Telegram bot commands set successfully!")


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
    
    if not resources.data:
        await update.message.reply_text("✅ No new processed resources. You're all caught up!")
        return

    keyboard = [
        [InlineKeyboardButton(resource["title"], callback_data=f"view_resource_{resource['id']}")]
        for resource in resources.data
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 **Select a resource to view:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

from telegram import CallbackQuery

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

async def handle_resource_selection(update: Update, context: CallbackContext):
    """Handles the selection of a resource and presents further actions."""
    query: CallbackQuery = update.callback_query
    user_telegram_id = query.from_user.id

    logging.info(f"📥 Received resource selection query: {query.data}")

    # ✅ Extract and ensure `resource_id` is an integer
    if query.data.startswith("view_resource_"):
        try:
            resource_id = int(query.data.replace("view_resource_", ""))
            logging.info(f"✅ Extracted Resource ID: {resource_id}")
        except ValueError:
            logging.error("❌ Invalid resource ID format.")
            await query.answer("❌ Invalid resource ID format.")
            return
    else:
        logging.error("❌ Invalid request format received.")
        await query.answer("❌ Invalid request format.")
        return

    # ✅ Fetch user ID from Supabase
    user_data = supabase_client.table("users") \
        .select("id") \
        .eq("telegram_id", user_telegram_id) \
        .execute()

    if not user_data.data:
        await query.answer("❌ User not found.")
        return

    user_id = user_data.data[0]["id"]

    # ✅ Fetch the resource details
    resource = supabase_client.table("resources") \
        .select("id, title, url, summary") \
        .eq("id", resource_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()

    logging.info(f"📖 Retrieved resource: {resource}")

    if not resource.data:
        await query.answer("❌ Resource not found.")
        return

    # ✅ Mark the resource as viewed
    supabase_client.table("resources").update({"is_viewed": True}) \
        .eq("id", resource_id) \
        .execute()

    # ✅ Create action buttons
    keyboard = [
        [InlineKeyboardButton("📜 Get TL;DR", callback_data=f"get_tldr_{resource_id}")],
        [InlineKeyboardButton("📄 View PDF", callback_data=f"view_pdf_{resource_id}")],
        [InlineKeyboardButton("🔗 Explore Related Topics", callback_data=f"explore_topics_{resource_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"📖 **{resource.data['title']}**\n🔗 [{resource.data['url']}]({resource.data['url']})\n\n"
    message += "What would you like to do next? 👇"

    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    await query.answer()


# ✅ Function to handle user clicking "Get TL;DR"
async def handle_tldr_request(update: Update, context: CallbackContext):
    """Sends a TL;DR of the selected resource."""
    query: CallbackQuery = update.callback_query
    resource_id = query.data.replace("get_tldr_", "")

    # ✅ Fetch TL;DR from Supabase
    resource = supabase_client.table("resources") \
        .select("summary") \
        .eq("id", resource_id) \
        .single() \
        .execute()

    if not resource.data:
        await query.answer("❌ TL;DR not available.")
        return

    message = f"📜 **TL;DR:**\n{resource.data['summary']}"
    await query.message.reply_text(message, parse_mode="Markdown")
    await query.answer()


from telegram import CallbackQuery

async def handle_pdf_request(update: Update, context: CallbackContext):
    """Handles a user's request to view a PDF of the enriched resource."""
    query: CallbackQuery = update.callback_query
    user_telegram_id = query.from_user.id

    logging.info(f"📥 Received PDF request. Query Data: {query.data}")

    # ✅ Extract and Convert resource_id to an integer
    if query.data.startswith("view_pdf_"):
        try:
            resource_id = int(query.data.replace("view_pdf_", ""))
            logging.info(f"✅ Extracted Resource ID: {resource_id}")
        except ValueError:
            logging.error("❌ Invalid resource ID format.")
            await query.answer("❌ Invalid resource ID format.")
            return
    else:
        logging.error("❌ Invalid request format received.")
        await query.answer("❌ Invalid request format.")
        return

    # ✅ Fetch user ID from Supabase
    try:
        user_data = supabase_client.table("users") \
            .select("id") \
            .eq("telegram_id", user_telegram_id) \
            .execute()

        if not user_data.data:
            logging.error("❌ User not found in the database.")
            await query.answer("❌ User not found.")
            return

        user_id = user_data.data[0]["id"]
        logging.info(f"✅ User ID: {user_id}")

    except Exception as e:
        logging.error(f"❌ Supabase query error (user lookup): {e}")
        await query.answer("❌ Internal error. Please try again.")
        return

    # ✅ Fetch PDF URL from Supabase
    try:
        resource = supabase_client.table("resources") \
            .select("pdf_url") \
            .eq("id", resource_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if resource.data and resource.data.get("pdf_url"):
            pdf_url = resource.data["pdf_url"]
            logging.info(f"📄 PDF already exists: {pdf_url}")

            await query.message.reply_text(
                f"📄 Your learning resource is ready! [Download PDF]({pdf_url})",
                parse_mode="Markdown"
            )
            await query.answer()
            return  # ✅ Exit early since PDF is already available
        else:
            logging.info("⚠️ PDF not found. Proceeding with generation.")

    except Exception as e:
        logging.error(f"❌ Supabase query error (PDF lookup): {e}")
        await query.answer("❌ Error retrieving PDF. Please try again.")
        return

    # ✅ Fetch enrichment data for the resource
    try:
        enrichment_data = supabase_client.table("ai_enrichments") \
            .select("*") \
            .eq("resource_id", resource_id) \
            .single() \
            .execute()

        if not enrichment_data.data:
            logging.error("❌ No enrichment data found. Cannot generate PDF.")
            await query.answer("❌ No enrichment data found. Cannot generate PDF.")
            return

        enriched_content = enrichment_data.data
        logging.info(f"✅ Enrichment data found for Resource ID: {resource_id}")

    except Exception as e:
        logging.error(f"❌ Supabase query error (enrichment lookup): {e}")
        await query.answer("❌ Error retrieving enrichment data. Please try again.")
        return

    # ✅ Generate PDF
    try:
        logging.info(f"📝 Generating PDF for Resource ID: {resource_id}")
        pdf_buffer = generate_pdf(user_id, resource_id, enriched_content)
        logging.info("✅ PDF successfully generated.")

    except Exception as e:
        logging.error(f"❌ PDF generation error: {e}")
        await query.answer("❌ Failed to generate PDF.")
        return

    # ✅ Upload PDF to Supabase
    try:
        logging.info(f"📤 Uploading PDF for Resource ID: {resource_id}")
        pdf_url = upload_pdf_to_supabase(user_id, resource_id, pdf_buffer)
        # pdf_url = save_pdf_locally(user_id, resource_id, pdf_buffer)

        # ✅ Store the new URL in the database
        supabase_client.table("resources") \
            .update({"pdf_url": pdf_url}) \
            .eq("id", resource_id) \
            .execute()

        logging.info(f"✅ PDF uploaded successfully: {pdf_url}")

        await query.message.reply_text(
            f"📄 Your learning resource is ready! [Download PDF]({pdf_url})",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"❌ Error uploading PDF to Supabase: {e}")
        await query.answer("❌ Failed to upload PDF.")
        return

    await query.answer()  # ✅ Closes the button interaction


# ✅ Function to handle user clicking "Explore Related Topics"
async def handle_explore_topics(update: Update, context: CallbackContext):
    """Fetches related topics based on enrichment."""
    query: CallbackQuery = update.callback_query
    # resource_id = query.data.replace("explore_topics_", "")

    # # ✅ Fetch Related Concepts from Supabase
    # resource = supabase_client.table("resources") \
    #     .select("enriched_data") \
    #     .eq("id", resource_id) \
    #     .single() \
    #     .execute()

    # if not resource.data or not resource.data["enriched_data"]:
    #     await query.answer("❌ No related topics found.")
    #     return

    # enriched_data = resource.data["enriched_data"]
    # related_concepts = enriched_data.get("related_concepts", [])

    # if not related_concepts:
    #     await query.answer("❌ No related topics found.")
    #     return

    # message = "🔗 **Explore Related Topics:**\n"
    # for concept in related_concepts:
    #     message += f"• {concept}\n"

    # await query.message.reply_text(message, parse_mode="Markdown")
    await query.answer("❌ No related topics found.")
    await query.answer()

# ✅ Handle Incoming Text Messages
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


# ✅ Register Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("queue_status", queue_status))
telegram_app.add_handler(CommandHandler("latest_resources", show_latest_processed_resources_list))
telegram_app.add_handler(CallbackQueryHandler(handle_resource_selection, pattern="view_resource_"))
telegram_app.add_handler(CallbackQueryHandler(handle_tldr_request, pattern="get_tldr_"))
telegram_app.add_handler(CallbackQueryHandler(handle_pdf_request, pattern="view_pdf_"))
telegram_app.add_handler(CallbackQueryHandler(handle_explore_topics, pattern="explore_topics_"))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))




# ✅ Background Task to Start Telegram Bot
async def run_telegram_bot():
    """Runs the Telegram bot inside an asyncio event loop."""
    logging.info("🚀 Starting Telegram bot...")
    await telegram_app.initialize()
    await telegram_app.start()
    await set_telegram_commands()  # Register commands when bot starts
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, poll_interval=5)


# ✅ FastAPI Endpoint: Start Telegram Bot
async def start_bot():
    """Manually start the Telegram bot if it stops."""
    asyncio.create_task(run_telegram_bot())
    return {"message": "Telegram bot started!"}

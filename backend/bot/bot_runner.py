# src/bot/bot_runner.py

import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update

from bot.handlers.commands import start, queue_status, show_latest_processed_resources_list
from bot.handlers.callbacks import (
    handle_resource_selection, handle_tldr_request, handle_pdf_request, handle_explore_topics
)
from bot.handlers.messages import handle_message, handle_setup_response
from src.config.settings import settings
from telegram import BotCommand
from telegram.ext import CallbackContext

# ✅ Init Telegram Bot
TELEGRAM_BOT_TOKEN = settings.TELEGRAM.TELEGRAM_BOT_TOKEN.get_secret_value()
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def dispatch_message(update: Update, context: CallbackContext):
    if context.user_data.get("awaiting_setup"):
        await handle_setup_response(update, context)
    else:
        await handle_message(update, context)


def register_handlers():
    """Register all Telegram command, callback, and message handlers."""
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("queue_status", queue_status))
    telegram_app.add_handler(CommandHandler("latest_resources", show_latest_processed_resources_list))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dispatch_message))
    telegram_app.add_handler(CallbackQueryHandler(handle_resource_selection, pattern="view_resource_"))
    telegram_app.add_handler(CallbackQueryHandler(handle_tldr_request, pattern="get_tldr_"))
    telegram_app.add_handler(CallbackQueryHandler(handle_pdf_request, pattern="view_pdf_"))
    telegram_app.add_handler(CallbackQueryHandler(handle_explore_topics, pattern="explore_topics_"))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


async def run_telegram_bot():
    """Runs the Telegram bot inside an asyncio event loop."""
    logging.info("🚀 Starting Telegram bot...")
    register_handlers()
    await telegram_app.initialize()
    await telegram_app.start()
    await set_telegram_commands()
    await telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES, poll_interval=5)


async def start_bot():
    """FastAPI-compatible trigger to run the Telegram bot."""
    asyncio.create_task(run_telegram_bot())
    return {"message": "Telegram bot started!"}


async def set_telegram_commands():
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("queue_status", "Show processing queue status"),
        BotCommand("latest_resources", "Show latest processed resources")
    ]
    await telegram_app.bot.set_my_commands(commands)
    logging.info("✅ Telegram bot commands set successfully!")


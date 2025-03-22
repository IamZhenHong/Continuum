from telegram import Update
from telegram.ext import CallbackContext
import httpx
import logging
from src.services.messages import store_message
from src.schemas import MessageCreate

async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    user_id = update.message.from_user.id

    payload = MessageCreate(user_id=user_id, message=message_text, message_type="text")

    try:
        
        response = await store_message(payload)
        logging.info(f"📤 Stored message: {response}")
        
        
        
    except httpx.HTTPError as e:
        print("🚨 API Request Error:", str(e))
        await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")


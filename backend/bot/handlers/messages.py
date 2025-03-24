from telegram import Update
from telegram.ext import CallbackContext
import httpx
import logging
from src.services.messages import store_message
from src.schemas import MessageCreate
from src.config.settings import supabase_client

async def handle_setup_response(update: Update, context: CallbackContext):
    """Handles user's one-time setup response after /start."""
    message_text = update.message.text
    user_id = update.effective_user.id

    # Save setup info to context or DB
    context.user_data["setup_info"] = message_text
    context.user_data["awaiting_setup"] = False

    # (Optional) Save to Supabase/Redis here if needed
    user = supabase_client.table("users").select("id").eq("telegram_id", user_id).execute()

    if not user.data:
        supabase_client.table("users").insert({"telegram_id": user_id, "setup_info": message_text}).execute()
    else:
        supabase_client.table("users").update({"setup_info": message_text}).eq("telegram_id", user_id).execute()
    

    await update.message.reply_text(
        f"✅ All set!\n\nHere's what you shared:\n\n“{message_text}”\n\nI'll personalize your learning journey from here 🧠🚀"
    )


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



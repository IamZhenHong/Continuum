from telegram import Update
from telegram.ext import CallbackContext
import httpx
import logging
from src.services.messages import store_message
from src.schemas import MessageCreate
from src.config.settings import supabase_client, redis_client
import asyncio


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

    # Case 1: Combined link + comment in one message
    if "http" in message_text and len(message_text.strip().split()) > 1:
        logging.info(f"🔗📝 Combined link + comment received from user {user_id}, storing immediately.")
        payload = MessageCreate(user_id=user_id, message=message_text, message_type="link")
        try:
            response = await store_message(payload)
            logging.info(f"📤 Stored combined message immediately: {response}")
        except httpx.HTTPError as e:
            logging.error(f"🚨 API Request Error: {str(e)}")
            await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")
        return

    # Case 2: Link-only message, maybe follow-up to buffered comment
    if "http" in message_text:
        buffered_comment = redis_client.get(f"pending_comment:{user_id}")
        if buffered_comment:
            if isinstance(buffered_comment, bytes):
                buffered_comment = buffered_comment.decode("utf-8")
            merged_message = f"{buffered_comment}\n{message_text}"
            redis_client.delete(f"pending_comment:{user_id}")
            logging.info(f"💬🔗 Merged link with buffered comment for user {user_id}")
            payload = MessageCreate(user_id=user_id, message=merged_message, message_type="link")
            try:
                response = await store_message(payload)
                logging.info(f"📤 Stored merged comment+link message: {response}")
            except httpx.HTTPError as e:
                logging.error(f"🚨 API Request Error: {str(e)}")
                await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")
        else:
            logging.info(f"🔗 Link-only message received from user {user_id}, buffering for 3s...")
            redis_client.setex(f"pending_link:{user_id}", 3, message_text)

            async def delayed_store():
                await asyncio.sleep(6)
                pending_link = redis_client.get(f"pending_link:{user_id}")
                pending_comment = redis_client.get(f"pending_comment:{user_id}")  # ⬅️ check again after delay

                if pending_link:
                    if isinstance(pending_link, bytes):
                        pending_link = pending_link.decode("utf-8")

                    # 🔁 Wait an extra beat for any comment to arrive
                    await asyncio.sleep(6)
                    pending_comment = redis_client.get(f"pending_comment:{user_id}")  # ⬅️ re-check

                    if pending_comment:
                        if isinstance(pending_comment, bytes):
                            pending_comment = pending_comment.decode("utf-8")
                        merged = f"{pending_comment}\n{pending_link}"
                        logging.info(f"🔁 Delayed merge: comment + link for user {user_id}")
                        redis_client.delete(f"pending_comment:{user_id}")
                    else:
                        merged = pending_link
                        logging.info(f"⌛ No comment found. Storing link-only message for user {user_id}")

                    redis_client.delete(f"pending_link:{user_id}")
                    payload = MessageCreate(user_id=user_id, message=merged, message_type="link")

                    try:
                        response = await store_message(payload)
                        logging.info(f"📤 Stored delayed message: {response}")
                    except httpx.HTTPError as e:
                        logging.error(f"🚨 API Request Error: {str(e)}")


            asyncio.create_task(delayed_store())
        return

    # Case 3: Text-only comment, maybe follow-up to a buffered link
    pending_link = redis_client.get(f"pending_link:{user_id}")
    if pending_link:
        if isinstance(pending_link, bytes):
            pending_link = pending_link.decode("utf-8")
        merged_message = f"{pending_link}\n{message_text}"
        redis_client.delete(f"pending_link:{user_id}")
        logging.info(f"🔗💬 Merged comment with previous link for user {user_id}")
        payload = MessageCreate(user_id=user_id, message=merged_message, message_type="link")
    else:
        # Buffer comment in case a link comes next
        logging.info(f"💬 Comment-only message buffered for user {user_id}")
        redis_client.setex(f"pending_comment:{user_id}", 3, message_text)
        return  # ⏳ Wait for link

    # Final fallback store (merged or plain text)
    try:
        response = await store_message(payload)
        logging.info(f"📤 Stored message: {response}")
    except httpx.HTTPError as e:
        logging.error(f"🚨 API Request Error: {str(e)}")
        await update.message.reply_text("⚠️ Failed to reach backend service. Please try again.")

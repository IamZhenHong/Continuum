
from src.services.resource_summarizer import extract_and_summarise_link
from src.config.settings import supabase_client
import src.schemas as schemas
from src.services.processing_tasks import add_to_processing_queue
from bot.telegram_interface import send_telegram_message

async def route_intent_action(data: schemas.IntentRouterRequest):
    """
    Routes the detected intent to the appropriate function.
    """

    if data.intent == "summarise_link":
        response = await extract_and_summarise_link(schemas.ExtractAndSummariseLinkRequest(message=data.message, user_id=data.user_id))
           # ✅ Send summary via Telegram bot
        send_telegram_message(data.user_id, f"📚 **Summary:**\n\n{response.diffbot_summary}")

        return {"status": "success", "message": "Summarized article", "data": response}
    elif data.intent == "add_to_processing_queue":
        return await add_to_processing_queue(data)
    
    # elif data.intent == "add_sources":
    #     return await add_sources(data)
    else:
        return {"status": "ignored", "reason": "No matching intent"}

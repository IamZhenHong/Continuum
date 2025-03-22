import logging
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.config.settings import supabase_client
import src.schemas as schemas
from src.services.intent.intent_classifier import classify_intent
from src.services.intent.intent_router import route_intent_action
# ✅ Initialize Router
from src.utils.text_processing import extract_url

async def store_message(data: schemas.MessageCreate):
    """
    Stores user messages and detects intent.

    - Checks if user exists in Supabase.
    - If user doesn't exist, creates a new user.
    - Calls `intent_router` to determine intent.
    - Saves the message with detected intent in Supabase.

    Args:
        data (MessageCreate): Pydantic model containing user_id, message, and type.

    Returns:
        dict: Success message with detected intent.
    """
    try:
        # ✅ Check if user exists
        user_response = supabase_client.table("users").select("id").eq("telegram_id", data.user_id).execute()
        user_id = user_response.data[0]["id"] if user_response.data else None

        # ✅ Create user if not found
        if not user_id:
            user_create_response = supabase_client.table("users").insert({
                "telegram_id": data.user_id,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            user_id = user_create_response.data[0]["id"]

        # ✅ Call intent_router with updated user_id
        data_dict = data.dict()
        data_dict["user_id"] = user_id
        resource_id = None

        # ✅ Update data dict with extracted resource_id
        data_dict = data.dict()
        data_dict["user_id"] = user_id
        data_dict["message"] = data.message
        data_dict["resource_id"] = resource_id
        # data_dict["link"] = url if url else None

        # ✅ Classify intent
        intent_response = await classify_intent(schemas.MessageCreate(**data_dict))
        detected_intent = intent_response.get("intent_detected", "unknown_intent")
        data_dict["intent"] = detected_intent
        # ✅ Store message with detected intent

        createdMessage = supabase_client.table("messages").insert({
            "user_id": user_id,
            "message": data.message,
            "message_type": data.message_type,
            "intent": detected_intent,
        }).execute()

        url = extract_url(data.message)

        print("URL", url)

        if url:
            resource_response = supabase_client.table("resources").insert({
                "user_id": user_id,
                "url": url,
                "created_at": datetime.utcnow().isoformat(),
                "message_id": createdMessage.data[0]["id"]
            }).execute()

            if resource_response.data:
                resource_id = resource_response.data[0]["id"]
                logging.info(f"🔗 Resource Inserted: {resource_id}")

        router_response = await route_intent_action(schemas.IntentRouterRequest(user_id=user_id,  intent=detected_intent,message=data.message, resource_id=resource_id))

        return {"message": "Stored successfully!", "intent": detected_intent}

    except Exception as e:
        logging.error(f"❌ Error storing message: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")


# ✅ Get messages for a user
async def get_messages(user_id: int):
    """
    Retrieves messages for a given user.

    Args:
        user_id (int): The user's ID.

    Returns:
        dict: List of messages for the user.
    """
    try:
        response = supabase_client.table("messages").select("*").eq("user_id", user_id).execute()
        messages = response.data or []

        if not messages:
            raise HTTPException(status_code=404, detail="No messages found")

        return {"messages": messages}

    except Exception as e:
        logging.error(f"❌ Error retrieving messages: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")


async def delete_message(message_id: int):
    """
    Deletes a user message by ID.

    Args:
        message_id (int): ID of the message to delete.

    Returns:
        dict: Success message or error if message is not found.
    """
    try:
        response = supabase_client.table("messages").delete().eq("id", message_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Deleted successfully!"}

    except Exception as e:
        logging.error(f"❌ Error deleting message: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")

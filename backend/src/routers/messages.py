



# ✅ Store user messages & detect intent
@app.post("/store_message")
async def store_message(data: schemas.MessageCreate):
    try:
        # ✅ Check if user exists
        user_response = supabase.table("users").select("id").eq("telegram_id", data.user_id).execute()
        user_id = user_response.data[0]["id"] if user_response.data else None

        # ✅ Create user if not found
        if not user_id:
            user_create_response = supabase.table("users").insert({
                "telegram_id": data.user_id,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            user_id = user_create_response.data[0]["id"]

        # ✅ Call intent_router with updated user_id
        data_dict = data.dict()
        data_dict["user_id"] = user_id
        intent_response = await intent_router(schemas.MessageCreate(**data_dict))
        detected_intent = intent_response.get("intent_detected", "unknown_intent")

        # ✅ Store message with detected intent
        supabase.table("messages").insert({
            "user_id": user_id,
            "message": data.message,
            "message_type": data.message_type,
            "intent": detected_intent
        }).execute()

        return {"message": "Stored successfully!", "intent": detected_intent}

    except Exception as e:
        print("❌ Error storing message:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")

# ✅ Retrieve user messages
@app.get("/messages/{user_id}")
async def get_messages(user_id: int):
    try:
        response = supabase.table("messages").select("*").eq("user_id", user_id).execute()
        messages = response.data or []
        return {"messages": messages} if messages else HTTPException(status_code=404, detail="No messages found")
    except Exception as e:
        print("❌ Error retrieving messages:", str(e))
        return HTTPException(status_code=500, detail="Unexpected Error")

# ✅ Delete a message
@app.delete("/delete_message/{message_id}")
async def delete_message(message_id: int):
    try:
        response = supabase.table("messages").delete().eq("id", message_id).execute()
        return {"message": "Deleted successfully!"} if response.data else HTTPException(status_code=404, detail="Message not found")
    except Exception as e:
        return HTTPException(status_code=500, detail="Unexpected Error")

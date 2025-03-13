from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import traceback
from src import schemas,bot
from openai import OpenAI
import re
from firecrawl import FirecrawlApp
import requests
import json
from urllib.parse import quote
import logging
from datetime import datetime


# ✅ Load Environment Variables
load_dotenv()

# ✅ Initialize FastAPI App
app = FastAPI()


# ✅ Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Supabase credentials not set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OpenAI()

firecrawl_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

diffbot_token = os.getenv("DIFFBOT_TOKEN")

@app.post("/store_message")
async def store_message(data: schemas.MessageCreate):
    try:
        # ✅ Check if user exists
        user_check_response = supabase.table("users").select("*").eq("telegram_id", data.user_id).execute()

        if not user_check_response or not user_check_response.data:
            print(f"⚠️ User {data.user_id} not found. Creating user...")

            # ✅ Create user
            user_create_response = supabase.table("users").insert({
                "telegram_id": data.user_id,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            if not user_create_response or "error" in user_create_response:
                raise HTTPException(status_code=500, detail="Failed to create new user.")

            print(f"✅ User {data.user_id} created successfully.")

        else:
            print(f"✅ User {data.user_id} already exists.")


        # ✅ Call `intent_router` to detect intent
        intent_response = await intent_router(data)
        print("🔍 Intent Router Response:", intent_response)

        detected_intent = intent_response.get('intent_detected', "unknown_intent")
        print("🤖 Detected Intent:", detected_intent)

        # ✅ Insert message into Supabase with intent
        insert_response = supabase.table("messages").insert({
            "user_id": data.user_id,
            "message": data.message,
            "message_type": data.message_type,
            "intent": detected_intent  # Store detected intent
        }).execute()

        print("🔍 Supabase Insert Response:", insert_response)

        if not insert_response or "error" in insert_response:
            raise HTTPException(status_code=500, detail="Message could not be stored in the database.")

        # ✅ Prepare the final response
        response_data = {
            "message": "Stored successfully!",
            "intent": detected_intent
        }

        return response_data

    except Exception as e:
        print("❌ Error storing message:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")

# ✅ Retrieve Messages by user_id
@app.get("/messages/{user_id}")
async def get_messages(user_id: int):
    try:
        response = supabase.table("messages").select("*").eq("user_id", user_id).execute()

        if response.get("error"):
            raise HTTPException(status_code=500, detail="Database Query Failed")

        messages = response.data
        if not messages:
            raise HTTPException(status_code=404, detail="No messages found for this user")

        return {"messages": messages}

    except Exception as e:
        print("❌ Error retrieving messages:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")


# ✅ Delete Message by ID
@app.delete("/delete_message/{message_id}")
async def delete_message(message_id: int):
    try:
        response = supabase.table("messages").delete().eq("id", message_id).execute()

        if response.get("error"):
            raise HTTPException(status_code=500, detail="Database Delete Failed")

        if not response.data:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Deleted successfully!"}

    except Exception as e:
        print("❌ Error deleting message:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")


# ✅ Update Message by ID
@app.put("/update_message/{message_id}")
async def update_message(message_id: int, data: schemas.MessageCreate):
    try:
        response = supabase.table("messages").update({
            "message": data.message,
            "message_type": data.message_type
        }).eq("id", message_id).execute()

        if response.get("error"):
            raise HTTPException(status_code=500, detail="Database Update Failed")

        if not response.data:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Updated successfully!"}

    except Exception as e:
        print("❌ Error updating message:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected Error")

def extract_url(text: str):
    url_pattern = r"(https?://[^\s]+)"  # Regex for extracting URLs
    match = re.search(url_pattern, text)
    
    if match:
        url = match.group(0).rstrip('.,)')  # Strip trailing dots, commas, and parentheses
        return url

    return None  # Return None if no URL found

@app.post("/summarise_link")
async def summarise_link(data: schemas.SummariseLinkRequest):
    message = data.message

    # ✅ Extract URL from message
    url = extract_url(message)
    
    if not url:
        raise HTTPException(status_code=400, detail="No valid URL found in the message.")

    print(f"🔗 Extracted URL: {url}")

    # ✅ Encode URL for Diffbot API
    encoded_url = quote(url)
    diffbot_url = f"https://api.diffbot.com/v3/analyze?url={encoded_url}&token={diffbot_token}"
    
    headers = {"Content-Type": "application/json"}

    # ✅ Make the API Request to Diffbot
    diffbot_response = requests.get(diffbot_url, headers=headers)

    if diffbot_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching data from Diffbot.")

    diffbot_data = diffbot_response.json()

    # ✅ Extract meaningful content
    extracted_text = extract_diffbot_text(diffbot_data)

    if not extracted_text:
        raise HTTPException(status_code=500, detail="Failed to extract meaningful text.")

    print("🧠 Extracted Content:", extracted_text[:500])  # Print a preview

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI summarizer. Summarize the following text."},
            {"role": "user", "content": extracted_text}
        ],
    )

    summary = response.choices[0].message.content

    bot.send_telegram_message(data.user_id, f"📚 **Summary of the article:**\n\n{summary}" )
                              
    return {
        "extracted_url": url,
        "diffbot_summary": extracted_text,
    }

# ✅ Helper function to extract meaningful text from Diffbot response
def extract_diffbot_text(response_data):
    """
    Extracts the main text content from the Diffbot API response.
    """
    try:
        if "objects" in response_data and len(response_data["objects"]) > 0:
            return response_data["objects"][0].get("text", "No text found")
        else:
            return "No valid content found in the response."
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return "Error extracting content."


async def intent_router(data: schemas.IntentRouterRequest):
    functions = ["summarise_link", "ask question", "add_sources", "add_to_learning"]

    system_prompt = f"""
    You are an AI **intent classifier**. Your sole task is to analyze user messages and **route them to the correct function**. 

    ⚠️ **STRICT INSTRUCTIONS:**
    - **DO NOT** summarize, answer questions, or take any action beyond selecting a function.
    - **ONLY return the function name** from the predefined list. **Nothing else.**
    - **If no function applies, return "unknown_intent"**.

    🎯 **Available Functions:**
    - **summarize_link** → When user wants to summarize an article or link.
    - **add_to_learning** → When user wants to save a topic or resource for later learning.
    - **add_sources** → When user wants to add new sources for tracking information.

    📌 **Example Inputs & Expected Outputs:**
    ✅ User: "Summarize this article: https://example.com"
    ➡️ Output: **summarize_link**

    ✅ User: "I want to save this topic for later"
    ➡️ Output: **add_to_learning**

    ✅ User: "Add this blog as a source for AI updates"
    ➡️ Output: **add_sources**

    ✅ User: "Hey, how's the weather?"
    ➡️ Output: **unknown_intent** 

    **Output Format:** **Return ONLY the function name. NO explanations, NO extra words.**
    """

    user_prompt = f"""
    Identify the correct function for this user message:

    \"\"\"{data.message}\"\"\"

    Return ONLY the function name from the list below:
    - summarize_link
    - add_to_learning
    - add_sources
    - unknown_intent
    """

    print("System Prompt:", system_prompt)
    print("User Prompt:", user_prompt)

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format=schemas.LlmIntentClassifierResponse
    )

    intent = response.choices[0].message.parsed.function_name
    print("Intent Detected:", intent)

    result = {
        "status": "success",
        "intent_detected": intent,
        "message": "Intent classification completed successfully."
    }

    if intent == "summarize_link":
        response = await summarise_link(data)
        result.update({
            "summary_text": response.get("diffbot_summary", "No summary found."),
            "source_url": response.get("extracted_url", "No URL found."),
            "additional_info": "Summary generated successfully."
        })
    else:
        result.update({
            "additional_info": "Function not implemented yet.",
        })

    return result

        


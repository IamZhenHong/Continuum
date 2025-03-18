import logging
from fastapi import APIRouter, HTTPException
from src.config.settings import openai_client
from src.schemas import IntentRouterRequest


# ✅ Intent Router: Classifies user intent
async def classify_intent(data: IntentRouterRequest):
    """
    Classifies user intent based on their message.

    - Uses OpenAI to determine which function should process the request.
    - Returns the function name or `unknown_intent` if no match is found.

    Args:
        data (IntentRouterRequest): The request containing the user's message.

    Returns:
        dict: Detected intent.
    """
    try:
        functions = ["summarise_link", "add_to_processing_queue", "add_sources"]

        system_prompt = f"""
        You are an **AI Intent Classifier**. Analyze user messages and **route them to the correct function**.

        **STRICT INSTRUCTIONS:**
        - **ONLY return the function name** from the list below.
        - **If no function applies, return "unknown_intent".**

        **Available Functions:**
        - summarise_link → For summarizing an article.
        - add_to_processing_queue → Add a resource to the processing queue.
        - add_sources → Add a source for tracking.
        - unknown_intent → If no function applies.

        **Example:**
        ✅ User: "Summarize this article: https://example.com"
        ➡️ Output: **summarise_link**
        """

        user_prompt = f"""
        Identify the correct function for this user message:

        \"\"\"{data.message}\"\"\"

        Return ONLY the function name from the list below:
        - summarise_link
        - add_to_processing_queue
        - add_sources
        - unknown_intent
        """

        logging.info(f"🔍 Classifying Intent: {data.message}")

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        intent = response.choices[0].message.content.strip()
        logging.info(f"✅ Detected Intent: {intent}")

        return {"intent_detected": intent}

    except Exception as e:
        logging.error(f"❌ Error classifying intent: {str(e)}")
        raise HTTPException(status_code=500, detail="Intent classification failed")

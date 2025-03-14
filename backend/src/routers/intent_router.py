
# ✅ Intent Router: Classifies user intent
async def intent_router(data: schemas.IntentRouterRequest):
    functions = ["summarise_link", "add_to_learning_queue", "add_sources"]

    system_prompt = f"""
    You are an **AI Intent Classifier**. Analyze user messages and **route them to the correct function**.

    **STRICT INSTRUCTIONS:**
    - **ONLY return the function name** from the list below.
    - **If no function applies, return "unknown_intent".**

    **Available Functions:**
    - summarise_link → For summarizing an article.
    - add_to_learning_queue → Save a topic or resource.
    - add_sources → Add a source for tracking.
    - unknown_intent → If no function applies.

    **Example:**
    ✅ User: "Summarize this article: https://example.com"
    ➡️ Output: **summarise_link**
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": data.message}],
    )

    intent = response.choices[0].message.content.strip()
    return {"intent_detected": intent}


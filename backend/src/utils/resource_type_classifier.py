from src.config.settings import openai_client
import logging
import src.schemas as schemas

def classify_resource_type(resource_content: str):
    """
    Classifies the type of resource based on the message.

    - Uses OpenAI to determine the type of resource.
    - Returns the resource type or `unknown_resource` if no match is found.

    Args:
        data (ResourceClassifierRequest): The request containing the user's message.

    Returns:
        dict: Detected resource type.
    """
    try:
        system_prompt = """
You are an **AI Resource Classifier**. Analyze user messages and **classify the type of resource**.

**STRICT INSTRUCTIONS:**
- **ONLY return the resource type** from the list below.
- **If no type applies, return "unknown_resource".**

**Available Resource Types:**
- article → For articles or blog posts
- video → For video content (e.g. YouTube)
- podcast → For spoken audio content
- tweet → For short-form tweets or X threads
- opinion → For subjective perspectives or arguments
- insight → For thought pieces or mental models
- story → For narrative or personal journey
- framework → For guides, methods or repeatable playbooks
- research → For data-backed findings or papers
- list → For curated resources
- tool → For products, software, or tools
- announcement → For launches, updates, or new features
- unknown_resource → If unsure

Respond with just the resource type. No explanation. No extra text.
    """

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": resource_content}
            ]
        )

        raw_type = response.choices[0].message.content.strip().lower()

        logging.info(f"🧠 Classified resource type: {raw_type}")

        return raw_type

    except Exception as e:
        logging.error(f"❌ Error in classify_resource_type: {str(e)}")
        return {"resource_type": "unknown_resource"}

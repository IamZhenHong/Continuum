import logging
from src import schemas
from src.config.settings import openai_client, supabase_client
from src.services.summarise import extract_and_summarise_link

async def enrich(data: schemas.EnrichResourceRequest):
    """
    Enriches a resource with additional data.

    - Calls the enrichment engine to process the resource.
    - Updates the resource with enriched data in Supabase.

    Args:
        data (EnrichResourceRequest): The request containing the resource ID.

    Returns:
        dict: Enrichment status and enriched data.
    """
    try:
        logging.info(f"🔄 Starting enrichment for Resource ID: {data.resource_id}")

        processed_resource = await extract_and_summarise_link(data)
        # ✅ Call OpenAI Enrichment Engine
        response = openai_client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": """You are an **AI Enrichment Engine**. Your job is to extract **key learning elements** from a given resource.

For the resource below, extract:
1️⃣ **Main Concept** - The **primary idea or theme** the resource is about.
2️⃣ **Key Keywords** - **Most relevant terms** that define this resource (max 5-8).
3️⃣ **Related Concepts** - Ideas **closely linked** to this resource 
   (e.g., if the topic is "Lean Startup," related concepts could be "MVP, PMF, Rapid Iteration").
4️⃣ **Follow-Up Questions** - Thought-provoking **questions** that a learner might ask after reading this.
5️⃣ **Actionable Insights** - Practical **takeaways** that can be **applied**.
"""
        },
        {
            "role": "user",
            "content": f"Enrich resource with content: {processed_resource.get('url_content', 'No content available')}"
        }
    ],
    response_format=schemas.EnrichedResourceResponse
)

        # ✅ Validate API Response
        if not response or not response.choices:
            logging.error(f"❌ OpenAI API returned an unexpected response: {response}")
            return {"status": "error", "message": "OpenAI API failed to return choices."}

        content = response.choices[0].message.parsed

        print("Content", content)

        supabase_client.table("ai_enrichments").insert({
            "resource_id": data.resource_id,
            "main_concept": content.main_concept,
            "key_keywords": content.key_keywords,
            "related_concepts": content.related_concepts,
            "follow_up_questions": content.follow_up_questions,
            "actionable_insights": content.actionable_insights,
        }).execute()

        if not content:
            logging.error(f"❌ OpenAI API returned an empty enrichment response for Resource ID: {data.resource_id}")
            return {"status": "error", "message": "OpenAI API returned an empty response."}

        logging.info(f"✅ Enrichment successful for Resource ID: {data.resource_id}")
        return content

    except ValueError as ve:
        logging.error(f"❌ JSON Parsing Error: {str(ve)}")
        return {"status": "error", "message": "Invalid response format from OpenAI API."}

    except Exception as e:
        logging.error(f"❌ Unexpected Error in enrichment: {str(e)}")
        return {"status": "error", "message": "An unexpected error occurred during enrichment."}


def enrich_subresources(data: schemas.EnrichSubresourcesRequest):
    """
    Enriches subresources of a main resource.

    Args:
        data (EnrichSubresourcesRequest): The request containing the main resource ID.

    Returns:
        dict: Enrichment status and enriched data.
    """
    urls = extract_urls()
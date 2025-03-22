import logging
from src import schemas
from src.config.settings import openai_client, supabase_client
from src.services.resource_summarizer import extract_and_summarise_link
import traceback
from src.utils.resource_type_classifier import classify_resource_type
from src.utils.schema_generator import generate_dynamic_schema
import pydantic

def enrich(data: schemas.EnrichResourceRequest):
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
        logging.info(f"📥 Enrichment Input Data: user_id={data.user_id}, message={data.message}")

        # ✅ Extract and summarise resource
        processed_resource = extract_and_summarise_link(schemas.ExtractAndSummariseLinkRequest(
            user_id=data.user_id,
            message=data.message,
            resource_id=data.resource_id
        ))

        logging.info(f"📦 Extracted Resource: {processed_resource}")

        # ✅ Classify resource type
        resource_type = classify_resource_type(processed_resource.get("url_content"))
        logging.info(f"🔍 Resource Type: {resource_type}")

        supabase_client.table("resources").update({
            "type": resource_type
        }).eq("id", data.resource_id).execute()

        # ✅ Get dynamic enrichment schema
        enrichment_schema = generate_dynamic_schema(resource_type, data.message, processed_resource.get("url_content"))
        # dynamic_enrichment_schema = parse_enrichment_response(enrichment_schema)


        if not processed_resource.get("url_content"):
            logging.warning(f"⚠️ No 'url_content' found for resource {data.resource_id}. Skipping enrichment.")
            return {"status": "error", "message": "No URL content to enrich."}

        # ✅ Prepare enrichment prompt
        user_prompt = f"Enrich resource with content: {processed_resource.get('url_content', 'No content available')}"
        logging.info("🧠 Sending prompt to OpenAI...")



        # ✅ Call OpenAI Enrichment Engine
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an **AI Enrichment Engine**. Your job is to extract **key learning elements** from a given resource. Based on the content of the resource, dynamically generate and output the corresponding enrichment schema in JSON format. The schema should contain the appropriate fields based on the resource, and for each field, provide meaningful content extracted from the resource.

{enrichment_schema}

"""
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format= {"type": "json_object"}

        )

        if not response or not response.choices:
            logging.error(f"❌ OpenAI API returned an unexpected response: {response}")
            return {"status": "error", "message": "OpenAI API failed to return choices."}

        content = response.choices[0].message.content
        logging.info(f"✅ Enrichment Result: {content}")

        supabase_response = supabase_client.table("ai_enrichments").insert({
            "dynamic_enrichment_data": content,
            "resource_id": data.resource_id
        }).execute()

        logging.info(f"📤 Supabase Insert Response: {supabase_response}")

        if not content:
            logging.error(f"❌ OpenAI returned empty enrichment data for Resource ID: {data.resource_id}")
            return {"status": "error", "message": "OpenAI returned empty content."}

        logging.info(f"✅ Enrichment completed successfully for Resource ID: {data.resource_id}")
        return content

    except ValueError as ve:
        logging.error(f"❌ JSON Parsing Error: {str(ve)}")
        return {"status": "error", "message": "Invalid response format from OpenAI API."}

    except Exception as e:
        logging.error(f"❌ Unexpected Error in enrichment: {str(e)}")
        logging.error(traceback.format_exc())
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
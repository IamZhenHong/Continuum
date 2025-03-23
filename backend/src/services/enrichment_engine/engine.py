import logging
import traceback
import json
import pydantic

from src import schemas
from src.config.settings import openai_client, supabase_client
from src.services.resource_summarizer import extract_and_summarise_link
from src.utils.resource_type_classifier import classify_resource_type
from src.utils.schema_generator import generate_dynamic_schema
from src.utils.text_processing import extract_urls, extract_diffbot_text

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
        logging.info("🧑‍💻 Extracting and summarizing resource...")
        processed_resource = extract_and_summarise_link(schemas.ExtractAndSummariseLinkRequest(
            user_id=data.user_id,
            message=data.message,
            resource_id=data.resource_id
        ))
        logging.debug(f"📦 Extracted Resource: {processed_resource}")

        # ✅ Classify resource type
        logging.info("🔍 Classifying resource type...")
        resource_type = classify_resource_type(processed_resource.get("url_content"))
        logging.info(f"🔍 Resource Type: {resource_type}")

        # Update resource type in Supabase
        logging.info("🔄 Updating resource type in Supabase...")
        supabase_client.table("resources").update({"type": resource_type}).eq("id", data.resource_id).execute()

        # ✅ Generate dynamic enrichment schema
        logging.info("🔄 Generating dynamic enrichment schema...")
        enrichment_schema = generate_dynamic_schema(
            resource_type,
            data.message,
            processed_resource.get("url_content")
        )

        if not processed_resource.get("url_content"):
            logging.warning(f"⚠️ No 'url_content' found for resource {data.resource_id}. Skipping enrichment.")
            return {"status": "error", "message": "No URL content to enrich."}

        # ✅ Prepare prompt
        user_prompt = f"Enrich resource with content: {processed_resource.get('url_content', 'No content available')}"
        logging.info("🧠 Sending prompt to OpenAI...")

        # ✅ Call OpenAI
        logging.info("🔄 Calling OpenAI for enrichment...")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an **AI Enrichment Engine**. Your job is to extract **key learning elements** from a given resource. "
                        "Based on the content of the resource, dynamically generate and output the corresponding enrichment schema in JSON format. "
                        "The schema should contain the appropriate fields based on the resource, and for each field, provide meaningful content extracted from the resource.\n\n"
                        f"{enrichment_schema}"
                    )
                },
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        if not response or not response.choices:
            logging.error(f"❌ OpenAI API returned an unexpected response: {response}")
            return {"status": "error", "message": "OpenAI API failed to return choices."}

        content = response.choices[0].message.content

        logging.info(f"✅ Primary Enrichment Result: {content}")


        # ✅ Enrich with primary links
        logging.info("🔄 Enriching with primary links...")
        secondary_enrichment_data = enrich_with_primary_links(schemas.EnrichWithPrimaryLinksRequest(
            resource_id = data.resource_id,
            message = data.message,
            enrichment_content = content
        ))

        if not secondary_enrichment_data:
            logging.error(f"❌ Enrichment failed — received empty response.")
            return {"status": "error", "message": "Secondary Enrichment failed."}
        

        logging.info(f"✅ Secondary Enrichment Result: {secondary_enrichment_data}")

        # ✅ Insert enriched data into Supabase
        logging.info("📤 Inserting enriched data into Supabase...")
        supabase_response = supabase_client.table("ai_enrichments").insert({
            "dynamic_enrichment_data": secondary_enrichment_data,
            "resource_id": data.resource_id
        }).execute()
        logging.info(f"📤 Supabase Insert Response: {supabase_response}")

        if not content:
            logging.error(f"❌ OpenAI returned empty enrichment data for Resource ID: {data.resource_id}")
            return {"status": "error", "message": "OpenAI returned empty content."}

        logging.info(f"✅ Enrichment completed successfully for Resource ID: {data.resource_id}")

        return {"status": "success", "message": "Resource enriched and updated successfully."}

    except ValueError as ve:
        logging.error(f"❌ JSON Parsing Error: {str(ve)}")
        return {"status": "error", "message": "Invalid response format from OpenAI API."}

    except Exception as e:
        logging.error(f"❌ Unexpected Error in enrichment: {str(e)}")
        logging.error(traceback.format_exc())
        return {"status": "error", "message": "An unexpected error occurred during enrichment."}

def enrich_with_primary_links(data: schemas.EnrichWithPrimaryLinksRequest):

    subresources = supabase_client.table("subresources").select("*").eq("resource_id", data.resource_id).execute()

    if not subresources.data:
        logging.warning(f"⚠️ No subresources found for resource {data.resource_id}. Skipping primary link enrichment.")
        return {"status": "error", "message": "No subresources found."}
    
    subresource_summaries = [subresource["summary"] for subresource in subresources.data]

    # ✅ Prepare prompt
    # ✅ Prepare system & user messages
    system_prompt = """
    You are an AI Enrichment Engine.

    Your task is to refine and enhance a resource's enrichment by incorporating relevant insights from supplementary materials (subresources) and aligning with the user's stated intent or focus.

    Instructions:
    - Review the original enrichment content.
    - Analyze the subresource summaries to identify anything that helps clarify, contextualize, or deepen understanding.
    - Consider the user's message and focus areas. Add content that supports these themes.
    - Maintain the **original schema structure**. You may add new fields if they logically enhance understanding, but **do not remove or rename** existing ones.
    - Ensure the response remains **brief, meaningful, and informational** — these are secondary enrichments meant to supplement the original.
    - Output should be valid **JSON only**. No markdown, no explanation, no code blocks.
    """

    user_prompt = f"""
    Original Enrichment Data:
    {data.enrichment_content}

    Subresource Summaries:
    {subresource_summaries}

    User Message:
    {data.message}
    """

    logging.info("ENRICH WITH PRIMARY LINKS user_prompt: ", user_prompt)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    if not response or not response.choices:
        logging.error(f"❌ OpenAI API returned an unexpected response: {response}")
        return {"status": "error", "message": "OpenAI API failed to return choices."}
    
    content = response.choices[0].message.content

    return content





    

   


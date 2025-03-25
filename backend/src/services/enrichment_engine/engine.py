import logging
import traceback
import json
from openai import OpenAI

from src import schemas
from src.config.settings import openai_client, supabase_client
from src.services.resource_summarizer import preprocess_link
from src.utils.resource_type_classifier import classify_resource_type
from src.utils.schema_generator import generate_dynamic_schema
from src.utils.text_processing import extract_urls, extract_diffbot_text
from amem.memory_system import AgenticMemorySystem
from amem.retrievers import SimpleEmbeddingRetriever
from .amem_setup import memory_system

def enrich(data: schemas.EnrichResourceRequest):
    try:
        logging.info(f"\n\n🔄 Starting enrichment for Resource ID: {data.resource_id}")
        logging.info(f"📅 Input: user_id={data.user_id}, message={data.message}")

        # Step 1: Extract and summarize resource
        logging.info("🧑‍💻 Extracting and summarizing resource...")
        processed_resource = preprocess_link(
            schemas.ExtractAndSummariseLinkRequest(
                user_id=data.user_id,
                message=data.message,
                resource_id=data.resource_id
            )
        )

        url_content = processed_resource.get("url_content")
        logging.debug(f"Extracted Resource: {processed_resource}")

        # Add key concept to Agentic Memory

        
        logging.info("🧠 Adding Key Concept to memory...")
        memory_id = memory_system.create(processed_resource.get("key_concept"))

        memory = memory_system.read(memory_id)
        logging.info(f"🧠 Key Concept added to memory: {memory}")
        logging.info(f"🧠 Key Concept added to memory: {memory.content}")
        logging.info(f"🧠 Key Concept added to memory: {memory.tags}")
        logging.info(f"🧠 Key Concept added to memory: {memory.context}")
        logging.info(f"🧠 Key Concept added to memory: {memory.keywords}")
                     


        if not url_content:
            logging.warning(f"⚠️ No 'url_content' found for resource {data.resource_id}. Skipping enrichment.")
            return {"status": "error", "message": "No URL content to enrich."}
        

        # # Step 2: Classify resource type
        # logging.info("🔍 Classifying resource type...")
        # resource_type = classify_resource_type(url_content)
        # logging.info(f"🔍 Resource Type: {resource_type}")

        resource_type = processed_resource.get("resource_type")

        supabase_client.table("resources").update({"type": resource_type}).eq("id", data.resource_id).execute()

        # Step 3: Generate dynamic enrichment schema
        logging.info("🔄 Generating dynamic enrichment schema...")
        enrichment_schema = generate_dynamic_schema(resource_type, data.message, url_content)

        # Step 4: Call OpenAI for primary enrichment
        user_prompt = f"Enrich resource with content: {url_content}"
        logging.info("🧠 Calling OpenAI for primary enrichment...")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "You are an AI Enrichment Engine. Extract key learning elements from the resource and "
                    "generate a JSON object based on this schema:\n\n" + enrichment_schema)
                },
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        if not response or not response.choices:
            raise ValueError("OpenAI API failed to return choices.")

        primary_enrichment = response.choices[0].message.content
        logging.info(f"✅ Primary Enrichment Result: {primary_enrichment}")

        # Step 5: Enrich using subresources
        logging.info("🔄 Enriching with primary links...")
        secondary_enrichment = enrich_with_primary_links(schemas.EnrichWithPrimaryLinksRequest(
            resource_id=data.resource_id,
            message=data.message,
            enrichment_content=primary_enrichment
        ))

        if not secondary_enrichment:
            raise ValueError("Secondary enrichment failed.")

        logging.info(f"✅ Secondary Enrichment Result: {secondary_enrichment}")

        # Step 6: Enrich using Perplexity
        logging.info("🔄 Enriching with Perplexity...")
        tertiary_enrichment, sources = enrich_with_perplexity(schemas.EnrichWithPerplexityRequest(
            message=data.message,
            enrichment_content=secondary_enrichment
        ))

        # Generate a personalized TL;DR
        user_profile = supabase_client.table("users").select("setup_info").eq("id", data.user_id).execute().data[0]

        if not user_profile:
            user_profile = {"role": "User", "interests": "General"}

        tldr = generate_personalized_tldr(user_profile, tertiary_enrichment, processed_resource.get("summary"), data.message)
        logging.info(f"✅ Personalized TL;DR: {tldr}")

        # Step 7: Insert tl;dr into Supabase
        logging.info("📤 Inserting TL;DR into Supabase...")
        supabase_client.table("resources").update({"tldr": tldr}).eq("id", data.resource_id).execute()

        # Step 7: Insert final enrichment into Supabase
        logging.info("📤 Inserting enriched data into Supabase...")
        supabase_client.table("ai_enrichments").insert({
            "dynamic_enrichment_data": tertiary_enrichment,
            "resource_id": data.resource_id,
            "sources": sources
        }).execute()

        logging.info(f"✅ Enrichment completed successfully for Resource ID: {data.resource_id}")
        return {"status": "success", "message": "Resource enriched and updated successfully."}

    except Exception as e:
        logging.error(f"❌ Enrichment failed: {e}")
        logging.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


def enrich_with_primary_links(data: schemas.EnrichWithPrimaryLinksRequest):
    subresources = supabase_client.table("subresources").select("*").eq("resource_id", data.resource_id).execute()
    if not subresources.data:
        logging.warning(f"⚠️ No subresources found for resource {data.resource_id}.")
        return data.enrichment_content

    subresource_summaries = [s["summary"] for s in subresources.data]

    system_prompt = """
You are an AI Enrichment Engine.

Your task is to **refine and enhance** an existing enrichment by:
1. Incorporating relevant insights from provided subresources.
2. Respecting the user's original focus or intent.
3. Maintaining the overall JSON schema (add new fields only if they add value).

Guidelines:
- Be **short**, **contextual**, and **insightful**.
- Remove any fluff or repetition.
- Highlight only meaningful additions or improvements.
- Keep the output in **valid JSON** format only (no markdown or extra commentary).
"""

    user_prompt = f"""
🔹 Original Enrichment:
{data.enrichment_content}

🔹 Subresource Summaries:
{subresource_summaries}

🔹 User Message (Focus):
{data.message}

Instructions:
- Use the subresource summaries to improve or expand the original enrichment only where useful.
- Pay special attention to what the user message is emphasizing — tailor the content accordingly.
- The final output should be a refined JSON object that better serves the user's intent.
"""


    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content if response and response.choices else data.enrichment_content


def enrich_with_perplexity(data: schemas.EnrichWithPerplexityRequest):
    try:
        perplexity_client = OpenAI(
            api_key="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",
            base_url="https://api.perplexity.ai"
        )
        


        perplexity_response = perplexity_client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": f"""
                        You are an AI assistant that performs research and supplements key insights.

                        Given a piece of enriched content and a user's learning intent, your job is to:

                        - Extract the **main concept** they want to understand
                        - Identify **5 relevant, recent, and credible** links that help **explain, extend, or apply** that concept
                        - Focus on materials that support **practical understanding** — such as articles, docs, guides, or explainers
                        """},
                {"role": "user", "content": f"""
                        ## USER GOAL
                        {data.message}

                        ## ENRICHED CONTENT
                        {data.enrichment_content}

                        🔍 Based on what the user wants to understand, extract the **main concept**, 
                        then provide 5 helpful and relevant links that offer more depth, examples, or explanation for that topic.
                        """
                }
            ]
        )

        if not perplexity_response or not perplexity_response.choices:
            raise ValueError("Perplexity returned no content.")

        research_content = perplexity_response.choices[0].message.content.strip()

        sources = perplexity_response.citations
        if not sources:
            sources = ["No specific source provided"]

        # Use OpenAI to integrate research into enrichment
        openai_prompt = f"""
        You are an AI Enrichment Engine.

        1. Existing Enrichment:
        {data.enrichment_content}

        2. Research (from Perplexity):
        {research_content}

        3. User Message:
        {data.message}

        Enhance the enrichment with any useful additions. Return valid JSON only.
        """

        openai_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI Enrichment Engine."},
                {"role": "user", "content": openai_prompt}
            ],
            response_format={"type": "json_object"}
        )

        return openai_response.choices[0].message.content if openai_response and openai_response.choices else data.enrichment_content, sources

    except Exception as e:
        logging.exception(f"❌ Perplexity enrichment failed: {e}")
        return data.enrichment_content, sources


from openai import OpenAI
from src.config.settings import openai_client
import logging


def generate_personalized_tldr(user_profile: dict, enriched_content: str, original_content_summary: str, message: str):
    """
    Generates a personalized, byte-sized TL;DR using GPT.

    Args:
        user_profile (dict): Dictionary containing 'role' and 'interests'.
        enriched_content (str): AI-enriched structured content.
        original_content (str): Raw extracted content from the resource.

    Returns:
        str: A TL;DR summary.
    """
    try:
        system_prompt = """
You are an AI assistant that creates ultra-concise, personalized TL;DRs for busy professionals.

🎯 Output format:
- 3 lines maximum
- Each line = one idea
- Line breaks MUST be used. No wrapping paragraphs.
- Last line = a short hook (<7 words) tailored to the user’s role or interest.

🧠 Tone:
- Clear, sharp, intelligent
- Like a senior operator giving you the essence fast
- Avoid marketing fluff, emojis, filler, or intros

⚠️ Rules:
- No markdown, no bullet points, no code blocks
- Do not exceed 3 lines
- Each line must be short, punchy, and direct
"""



        user_prompt = f"""
USER PROFILE:
{user_profile}

ENRICHED CONTENT:
{enriched_content}

ORIGINAL SUMMARY:
{original_content_summary}

USER MESSAGE (Context):
{message}

Goal: Return only a short, 2–3 sentence TL;DR as described.
"""


        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ Error generating TL;DR: {str(e)}")
        return "⚠️ Sorry, we couldn't generate a TL;DR at this time."

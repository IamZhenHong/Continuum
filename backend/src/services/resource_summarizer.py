import requests
from urllib.parse import quote
from fastapi import APIRouter, HTTPException
from src.config.settings import settings
from src.utils.text_processing import extract_url, extract_urls, extract_diffbot_text
import src.schemas as schemas
from openai import OpenAI
from src.config.settings import supabase_client


# ✅ Initialize OpenAI Client
openai_client = OpenAI(api_key=settings.OPENAI.OPENAI_API_KEY.get_secret_value())

def preprocess_link(data: schemas.ExtractAndSummariseLinkRequest):
    
    resource = get_resource(data.resource_id)
    print(resource)
    extracted_text = extract_main_content(resource["url"])

    subresource_urls = extract_urls(extracted_text)
    process_subresources(subresource_urls, data.resource_id)

    summary, title, resource_type, metadata, tags, key_concept = generate_metadata(extracted_text)
    update_resource_summary(data.resource_id, summary, title, resource_type, metadata, tags, key_concept)

    return {
        "extracted_url": resource["url"],
        "url_content": extracted_text,
        "summary": summary,
        "title": title,
        "resource_type": resource_type,
        "metadata": metadata,
        "tags": tags,
        "key_concept": key_concept
    }

def get_resource(resource_id: str):
    resource = supabase_client.table("resources").select("*").eq("id", resource_id).execute()
    if not resource.data:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return resource.data[0]

def extract_main_content(url: str):
    response = requests.get(f"https://api.diffbot.com/v3/analyze?url={quote(url)}&token={settings.DIFFBOT.DIFFBOT_TOKEN.get_secret_value()}")
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Diffbot failed.")
    text = extract_diffbot_text(response.json())
    if not text or text == "No text found":
        raise HTTPException(status_code=500, detail="No useful content.")
    return text

def generate_metadata(text: str) -> tuple[str, str]:
    response = openai_client.beta.chat.completions.parse(
        model=settings.OPENAI.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Generate summary,title, resource_type, metadata,tags, and key conepts from the text."},
            {"role": "user", "content": text},
        ],
        response_format=schemas.PreprocessResourceResponse
    )

    response = response.choices[0].message.parsed
    return response.summary, response.title,response.resource_type, response.metadata, response.tags, response.key_concept

def process_subresources(urls: list[str], parent_resource_id: str):
    for url in urls:
        text = extract_main_content(url)
        summary, title, metadata, tags, key_concept, resource_type = generate_metadata(text)
        supabase_client.table("subresources").insert({
            "resource_id": parent_resource_id,
            "url": url,
            "summary": summary,
            "type": resource_type,
            "title": title,
            "metadata": metadata,
            "tags": tags,
            "key_concept": key_concept
        }).execute()

def update_resource_summary(resource_id: str, summary: str, title: str, resource_type: str, metadata: dict, tags: list[str], key_concept: str):
    supabase_client.table("resources").update({
        "summary": summary,
        "title": title,
        "type": resource_type,
        "metadata": metadata,
        "tags": tags,
        "key_concept": key_concept

    }).eq("id", resource_id).execute()

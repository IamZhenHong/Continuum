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

def extract_and_summarise_link(data: schemas.ExtractAndSummariseLinkRequest):
    
    resource = get_resource(data.resource_id)
    print(resource)
    extracted_text = extract_main_content(resource["url"])

    subresource_urls = extract_urls(extracted_text)
    process_subresources(subresource_urls, data.resource_id)

    summary, title = generate_summary_and_title(extracted_text)
    update_resource_summary(data.resource_id, summary, title)

    return {
        "extracted_url": resource["url"],
        "url_content": extracted_text,
        "diffbot_summary": summary
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

def generate_summary_and_title(text: str) -> tuple[str, str]:
    response = openai_client.beta.chat.completions.parse(
        model=settings.OPENAI.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Summarize and title this content."},
            {"role": "user", "content": text},
        ],
        response_format=schemas.ProcessResourceResponse
    )
    return response.choices[0].message.parsed.summary, response.choices[0].message.parsed.title

def process_subresources(urls: list[str], parent_resource_id: str):
    for url in urls:
        text = extract_main_content(url)
        summary, title = generate_summary_and_title(text)
        supabase_client.table("subresources").insert({
            "resource_id": parent_resource_id,
            "url": url,
            "summary": summary,
            "title": title
        }).execute()

def update_resource_summary(resource_id: str, summary: str, title: str):
    supabase_client.table("resources").update({
        "summary": summary,
        "title": title
    }).eq("id", resource_id).execute()

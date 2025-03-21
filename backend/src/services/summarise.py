import requests
from urllib.parse import quote
from fastapi import APIRouter, HTTPException
from src.config.settings import settings
from src.utils.text_processing import extract_url, extract_urls, extract_diffbot_text
import src.schemas as schemas
from src.bot import send_telegram_message
from openai import OpenAI
from src.config.settings import supabase_client


# ✅ Initialize OpenAI Client
openai_client = OpenAI(api_key=settings.OPENAI.OPENAI_API_KEY.get_secret_value())

def extract_and_summarise_link(data: schemas.ExtractAndSummariseLinkRequest):
    """
    Summarizes an article by extracting content from a given link.

    Args:
        data (SummariseLinkRequest): The request body containing the user's message.

    Returns:
        dict: Extracted URL and summary text.
    """
    resource = supabase_client.table("resources").select("*").eq("id", data.resource_id).execute()
    if not resource.data:
        raise HTTPException(status_code=404, detail="Resource not found.")
    url = resource.data[0].get("url")
    if not url:
        raise HTTPException(status_code=400, detail="No valid URL found in the message.")
    # url = extract_url(data.message)
    # if not url:
    #     raise HTTPException(status_code=400, detail="No valid URL found in the message.")
    

    # ✅ Call Diffbot API to extract text
    diffbot_url = f"https://api.diffbot.com/v3/analyze?url={quote(url)}&token={settings.DIFFBOT.DIFFBOT_TOKEN.get_secret_value()}"
    diffbot_response = requests.get(diffbot_url)



    if diffbot_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching data from Diffbot API.")

    resource_extracted_text = extract_diffbot_text(diffbot_response.json())
    if not resource_extracted_text or resource_extracted_text == "No text found":
        raise HTTPException(status_code=500, detail="Failed to extract meaningful text.")
    
    subresource_urls = extract_urls(resource_extracted_text)


    if subresource_urls:
        print("Subresource URLs:", subresource_urls)
        for subresource_url in subresource_urls:
        
            diffbot_response = requests.get(f"https://api.diffbot.com/v3/analyze?url={quote(subresource_url)}&token={settings.DIFFBOT.DIFFBOT_TOKEN.get_secret_value()}")
            extracted_text = extract_diffbot_text(diffbot_response.json())

            response = openai_client.beta.chat.completions.parse(
                model=settings.OPENAI.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Summarize the following text and provide a title."},
                    {"role": "user", "content": extracted_text},
                ],
                response_format = schemas.ProcessSubresourceResponse
            )
            print("Response", response)
            response = supabase_client.table("subresources").insert({
                "resource_id": data.resource_id,
                "url": subresource_url,
                "summary": response.choices[0].message.parsed.summary,
                "title": response.choices[0].message.parsed.title
            }).execute()
            print("Subresource Response", response)




    # ✅ Call OpenAI to summarize extracted content
    print("Extracted Text!!!!!!!!!!!!!!!!!!!!!!", resource_extracted_text)
    response = openai_client.beta.chat.completions.parse(
        model=settings.OPENAI.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Summarize the following text and provide a title."},
            {"role": "user", "content": resource_extracted_text},
        ],
        response_format = schemas.ProcessResourceResponse
    )

    supabase_client.table("resources").update({
        "summary": response.choices[0].message.parsed.summary,
        "title": response.choices[0].message.parsed.title
    }).eq("id", data.resource_id).execute()

    return {
        "extracted_url": url,
        "url_content": resource_extracted_text,
        "diffbot_summary": response.choices[0].message.parsed.summary
    }

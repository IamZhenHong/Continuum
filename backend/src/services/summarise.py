import requests
from urllib.parse import quote
from fastapi import APIRouter, HTTPException
from src.config.settings import settings
from src.utils.text_processing import extract_url, extract_diffbot_text
import src.schemas as schemas
from src.bot import send_telegram_message
from openai import OpenAI



# ✅ Initialize OpenAI Client
openai_client = OpenAI(api_key=settings.OPENAI.OPENAI_API_KEY.get_secret_value())

async def extract_and_summarise_link(data: schemas.ExtractAndSummariseLinkRequest):
    """
    Summarizes an article by extracting content from a given link.

    Args:
        data (SummariseLinkRequest): The request body containing the user's message.

    Returns:
        dict: Extracted URL and summary text.
    """
    url = extract_url(data.message)
    if not url:
        raise HTTPException(status_code=400, detail="No valid URL found in the message.")

    # ✅ Call Diffbot API to extract text
    diffbot_url = f"https://api.diffbot.com/v3/analyze?url={quote(url)}&token={settings.DIFFBOT.DIFFBOT_TOKEN.get_secret_value()}"
    diffbot_response = requests.get(diffbot_url)

    if diffbot_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching data from Diffbot API.")

    extracted_text = extract_diffbot_text(diffbot_response.json())
    if not extracted_text or extracted_text == "No text found":
        raise HTTPException(status_code=500, detail="Failed to extract meaningful text.")

    # ✅ Call OpenAI to summarize extracted content
    response = openai_client.chat.completions.create(
        model=settings.OPENAI.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Summarize the following text."},
            {"role": "user", "content": extracted_text},
        ],
    )

    summary = response.choices[0].message.content

    return {
        "extracted_url": url,
        "url_content": extracted_text,
        "diffbot_summary": summary,
    }

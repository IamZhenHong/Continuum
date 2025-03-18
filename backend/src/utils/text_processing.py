import re
import logging
from typing import Optional, Dict, Any

def extract_url(text: str) -> Optional[str]:
    """
    Extracts the first valid URL from the given text.
    
    Args:
        text (str): The input text containing a possible URL.
    
    Returns:
        Optional[str]: The extracted URL, or None if no valid URL is found.
    """
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    return match.group(0).rstrip('.,)') if match else None

def extract_diffbot_text(response_data: Dict[str, Any]) -> str:
    """
    Extracts the main text content from a Diffbot API response.

    Args:
        response_data (Dict[str, Any]): The JSON response from Diffbot API.

    Returns:
        str: Extracted text content or an error message.
    """
    try:
        if "objects" in response_data and response_data["objects"]:
            return response_data["objects"][0].get("text", "No text found")
        return "No valid content found."
    except Exception as e:
        logging.error(f"❌ Error extracting text from Diffbot response: {e}")
        return "Error extracting content."

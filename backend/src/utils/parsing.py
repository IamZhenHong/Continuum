import re




def extract_url(text: str):
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    return match.group(0).rstrip('.,)') if match else None

# ✅ Helper: Extract text from Diffbot API response
def extract_diffbot_text(response_data):
    try:
        if "objects" in response_data and response_data["objects"]:
            return response_data["objects"][0].get("text", "No text found")
        return "No valid content found."
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return "Error extracting content."

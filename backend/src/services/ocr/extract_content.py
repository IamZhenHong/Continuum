from openai import OpenAI
from src.config.settings import settings
from src.utils.text_processing import extract_url, extract_urls, extract_diffbot_text
import src.schemas as schemas
from src.config.settings import supabase_client
import fitz

# ✅ Initialize OpenAI Client
openai_client = OpenAI(api_key=settings.OPENAI.OPENAI_API_KEY.get_secret_value())


client = OpenAI()



async def extract_content(
    data: schemas.ExtractWithOCRRequest,
):
    
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Extract all the text and images from the screenshot."},
                {
                    "type": "input_image",
                    "image_url": data.resource_url,
                },
            ],
        }],
    )

    return response.output_text
        
import requests
import fitz  # PyMuPDF
import os
from tempfile import NamedTemporaryFile

async def extract_text_from_pdf_pymudf(data: schemas.ExtractWithOCRRequest):
    """
    Extracts all the text from a PDF file.

    :param data: The request data containing the resource ID
    :return: Extracted text as a string
    """

    # Fetch the URL of the PDF from Supabase
    # resource = supabase_client.table("resources").select("*").eq("id", data.resource_id).execute()
    # pdf_url = resource.data[0]['url']  # Get the URL of the PDF file

    # Download the PDF file to a temporary location
    response = requests.get(data.resource_url)
    if response.status_code != 200:
        raise Exception("Failed to download the PDF file.")

    # Create a temporary file to store the downloaded PDF
    with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        temp_pdf.write(response.content)
        temp_pdf_path = temp_pdf.name  # Get the path of the temporary file

    # Open the downloaded PDF using PyMuPDF
    doc = fitz.open(temp_pdf_path)

    # Initialize an empty string to hold all the extracted text
    extracted_text = ""

    # Iterate through each page of the PDF
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)  # Load each page
        extracted_text += page.get_text()  # Extract text from the page

    # Optionally, delete the temporary file after processing
    os.remove(temp_pdf_path)

    return extracted_text

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from src.config.settings import supabase_client
import logging
from src.config.settings import settings
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime


import json
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from src.config.settings import supabase_client, openai_client

import json
from io import BytesIO
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os
import re



def ai_enrichment_to_html(enriched_data: dict) -> str:
    """
    Uses GPT to generate full HTML from enrichment data directly.
    Returns a complete HTML string with styling and structure.
    """
    prompt = f"""
You are an expert in HTML and technical writing.

Take the following AI enrichment data and write a full, styled HTML report.
The HTML must include:
- <html>, <head>, and <body> tags
- A header with title and subtitle
- Multiple content sections with headings and paragraphs
- Inline CSS styling for clean, modern PDF output (e.g., font-family: 'DejaVu Sans')
- Do not wrap the HTML in markdown or code blocks
- Do not explain anything, just return raw HTML

Enrichment data (JSON):
{json.dumps(enriched_data)}
    """

    response = openai_client.chat.completions.create(
        model=settings.OPENAI.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You turn structured AI enrichment into full HTML reports for PDF export."},
            {"role": "user", "content": prompt}
        ]
    )

    html_content = response.choices[0].message.content.strip()

    # Just in case GPT wrapped it in ```html, strip it
    html_content = re.sub(r"^```html", "", html_content).strip()
    html_content = re.sub(r"```$", "", html_content).strip()

    return html_content


def generate_pdf(user_id: int, resource_id: int, enriched_data: dict) -> BytesIO:
    """
    Converts GPT-generated HTML into a PDF and returns it in memory.
    """
    # Step 1: Generate styled HTML from enriched data
    html_content = ai_enrichment_to_html(enriched_data)

    # Step 2: Convert to PDF
    pdf_io = BytesIO()
    HTML(string=html_content).write_pdf(pdf_io)
    pdf_io.seek(0)
    return pdf_io

import io
import logging
from datetime import datetime
from src.config.settings import supabase_client

def upload_pdf_to_supabase(user_id: int, resource_id: int, pdf_buffer: io.BytesIO) -> str:
    """
    Uploads a generated PDF to Supabase storage.

    Args:
        user_id (int): The user's ID.
        resource_id (int): The resource ID.
        pdf_buffer (BytesIO): The generated PDF in memory.

    Returns:
        str: The public URL of the uploaded PDF.
    """
    try:
        # ✅ Ensure we are at the start of the PDF buffer
        pdf_buffer.seek(0)
        pdf_bytes = pdf_buffer.getvalue()  # ✅ Extract bytes from BytesIO

        # ✅ Define a unique file path in Supabase Storage
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"{user_id}/{resource_id}_{timestamp}.pdf"
        storage_path = f"pdfs/{pdf_filename}"  # Adjust bucket path

        logging.info(f"📤 Uploading PDF to Supabase Storage: {storage_path}")

        # ✅ Upload the file using bytes
        response = supabase_client.storage.from_("reports").upload(
            path=storage_path,
            file=pdf_bytes,  # ✅ Upload bytes instead of BytesIO object
            file_options={"content-type": "application/pdf"}
        )



        # ✅ Generate public URL
        pdf_url = supabase_client.storage.from_("reports").get_public_url(storage_path)
        logging.info(f"✅ PDF successfully uploaded to Supabase: {pdf_url}")

        return pdf_url

    except Exception as e:
        logging.error(f"❌ Error uploading PDF to Supabase: {e}")
        return None


import os
import io

def save_pdf_locally(user_id: int, resource_id: int, pdf_buffer: io.BytesIO) -> str:
    """
    Saves the generated PDF to a local directory instead of uploading to Supabase.

    Args:
        user_id (int): The user's ID.
        resource_id (int): The resource ID.
        pdf_buffer (BytesIO): The generated PDF in memory.

    Returns:
        str: The local file path of the saved PDF.
    """
    try:
        # ✅ Ensure directory exists
        save_dir = f"saved_pdfs/{user_id}/"
        os.makedirs(save_dir, exist_ok=True)  

        # ✅ Define file path
        file_path = os.path.join(save_dir, f"{resource_id}.pdf")

        # ✅ Save the PDF locally
        with open(file_path, "wb") as f:
            pdf_buffer.seek(0)  # Ensure we're at the start of the buffer
            f.write(pdf_buffer.read())  # Write PDF content to file

        logging.info(f"✅ PDF saved locally at: {file_path}")
        return file_path

    except Exception as e:
        logging.error(f"❌ Error saving PDF locally: {e}")
        return None

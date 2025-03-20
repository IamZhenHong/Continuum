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


def generate_pdf(user_id: int, resource_id: int, enriched_data: dict) -> BytesIO:
    """
    Generates a structured, professional PDF for a given resource with enrichment data.

    Args:
        user_id (int): The user ID.
        resource_id (int): The resource ID.
        enriched_data (dict): Enrichment data containing insights.

    Returns:
        BytesIO: The generated PDF in memory.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    content = []

    # ✅ Title
    title = Paragraph("<b>📖 Learning Resource Summary</b>", styles['Title'])
    content.append(title)
    content.append(Spacer(1, 12))

    # ✅ Metadata
    metadata = [
        ["Generated For:", f"User ID: {user_id}"],
        ["Date:", datetime.now().strftime("%Y-%m-%d")],
        ["Resource ID:", str(resource_id)],
    ]
    metadata_table = Table(metadata, colWidths=[100, 400])
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    content.append(metadata_table)
    content.append(Spacer(1, 12))

    # ✅ Add Enrichment Sections
    sections = [
        ("Main Concept", enriched_data.get("main_concept", "No concept available")),
        ("Key Keywords", ", ".join(enriched_data.get("key_keywords", []))),
        ("Related Concepts", ", ".join(enriched_data.get("related_concepts", []))),
        ("Follow-Up Questions", "\n".join(enriched_data.get("follow_up_questions", []))),
        ("Actionable Insights", "\n".join(enriched_data.get("actionable_insights", []))),
    ]

    for title, text in sections:
        content.append(Paragraph(f"<b>{title}:</b>", styles['Heading2']))
        content.append(Spacer(1, 5))
        content.append(Paragraph(text if text else "No data available", styles['Normal']))
        content.append(Spacer(1, 12))

    # ✅ Build and return PDF
    doc.build(content)
    buffer.seek(0)
    return buffer

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

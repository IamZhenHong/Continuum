
from src.services.ocr.extract_content import extract_text_from_pdf_pymudf, extract_content
from src.config.settings import supabase_client
import src.schemas as schemas
from src.utils.generate_summary import generate_summary

async def process_resource(user_id: int, document_url=None, image_url=None, caption=None):
    if document_url:
        try:
            content = await extract_text_from_pdf_pymudf(
                data=schemas.ExtractWithOCRRequest(
                    user_id=user_id,
                    resource_url=document_url,
                    message=caption,
                )
            )
            summary = await generate_summary(content)
            supabase_client.table("resources").insert({
                "user_id": user_id,
                "url": document_url,
                "summary": summary
            }).execute()
        except Exception as e:
            print(f"Error processing document URL: {e}")

    if image_url:
        try:
            content = await extract_content(
                data=schemas.ExtractWithOCRRequest(
                    user_id=user_id,
                    resource_url=image_url,
                    message=caption,
                )
            )
            summary = await generate_summary(content)
            supabase_client.table("resources").insert({
                "user_id": user_id,
                "url": image_url,
                "summary": summary
            }).execute()
        except Exception as e:
            print(f"Error processing image URL: {e}")

    if caption:
        try:
            supabase_client.table("messages").insert({
                "user_id": user_id,
                "message": caption
            }).execute()
        except Exception as e:
            print(f"Error processing caption: {e}")

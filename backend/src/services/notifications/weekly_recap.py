# src/services/notifications.py
from celery import shared_task
from src.config.settings import supabase_client, openai_client, settings
from bot.telegram_interface import send_telegram_message
from datetime import datetime, timedelta
import logging
from src.services.pdf_generation.generate_pdf import generate_pdf, upload_pdf_to_supabase_weekly_recap,ai_enrichment_to_html
from io import BytesIO
from weasyprint import HTML


@shared_task(name="weekly_recap.send_weekly_recap")
def send_weekly_recap():
    logging.info("📤 Starting to send weekly recaps to all users...")

    users = supabase_client.table("users").select("id").execute().data

    for user in users:
        user_id = user["id"]
        logging.info(f"👤 Processing user: {user_id}")
        try:
            # 1. Generate recap PDF
            pdf_buffer = generate_weekly_recap_pdf(user_id)

            if not pdf_buffer:
                logging.info(f"⏭️ No recap generated for user {user_id} — skipping.")
                continue

            # 2. Upload PDF and store metadata
            logging.info(f"📥 Uploading weekly recap for user {user_id}")
            pdf_url = upload_pdf_to_supabase_weekly_recap(user_id, pdf_buffer)

            if not pdf_url:
                logging.error(f"❌ Failed to upload weekly recap PDF for user {user_id}")
                continue

            # 3. Send Telegram message
            message = f"📅 Here's your [weekly recap PDF]({pdf_url})! Click to review what you've learned."
            logging.info(f"📨 Sending Telegram message with PDF link to user {user_id}")
            send_telegram_message(user_id, message)

            logging.info(f"✅ Recap sent to user {user_id}")

        except Exception as e:
            logging.exception(f"❌ Failed to send weekly recap to user {user_id}: {e}")


def generate_weekly_recap_pdf(user_id: str) -> bytes:
    logging.info(f"📚 Generating weekly recap PDF for user: {user_id}")

    today = datetime.utcnow()
    one_week_ago = today - timedelta(days=1)

    # 1. Fetch resources
    logging.info("🔍 Fetching processed resources from Supabase...")
    resource_resp = supabase_client.table("resources") \
        .select("id, summary, created_at,pdf_url") \
        .eq("user_id", user_id) \
        .gte("created_at", one_week_ago.isoformat()) \
        .eq("is_processed", True) \
        .order("created_at", desc=True) \
        .execute()

    resources = resource_resp.data or []
    logging.debug(f"📦 Retrieved {len(resources)} resources for user {user_id}")

    if not resources:
        logging.warning("📭 No resources found for this week.")
        return None

    recap_sections = []
    for resource in resources:
        logging.debug(f"📘 Processing resource: ({resource['id']})")

        enrichment_resp = supabase_client.table("ai_enrichments") \
            .select("dynamic_enrichment_data") \
            .eq("resource_id", resource["id"]) \
            .limit(1) \
            .execute()
    
        

        enrichment = enrichment_resp.data[0]["dynamic_enrichment_data"] if enrichment_resp.data else None
        logging.debug("🧠 Retrieved enrichment data." if enrichment else "⚠️ No enrichment found.")

        # GPT Summarization
        prompt = f"""
You are a personal AI learning assistant. Help summarize what the user learned from this resource this week.


Summary: {resource['summary']}

Enriched Content:
{enrichment or "No enrichment available."}

Write a short, helpful bullet-point recap for the user in plain English.
"""
        logging.debug("🧠 Calling OpenAI to summarize resource...")
        response = openai_client.chat.completions.create(
            model=settings.OPENAI.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an AI that summarizes a user's weekly learnings."},
                {"role": "user", "content": prompt}
            ]
        )

        recap_text = response.choices[0].message.content.strip()
        logging.debug(f"✅ GPT summary complete for resource: {resource['id']}")
        pdf_url = resource.get("pdf_url")
        recap_text = response.choices[0].message.content.strip()

        # Combine with PDF link
        if pdf_url:
            recap_text += f"\n📄 [View Full PDF Recap]({pdf_url})"
        else:
            recap_text += f"\n📄 No PDF available for this resource."

        recap_sections.append(f"🧠\n{recap_text}\n")

    final_text = "📅 **Here's what you learned this week:**\n\n" + "\n".join(recap_sections)

    # Generate PDF
    logging.info("🖨️ Generating PDF...")
    html_content = ai_enrichment_to_html(final_text)
    pdf_io = BytesIO()
    HTML(string=html_content).write_pdf(pdf_io)
    pdf_io.seek(0)
    return pdf_io
 

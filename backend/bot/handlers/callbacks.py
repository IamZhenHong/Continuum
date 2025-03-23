
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from src.config.settings import supabase_client
from src.services.pdf_generation.generate_pdf import generate_pdf, upload_pdf_to_supabase
import logging
import json

async def handle_resource_selection(update: Update, context: CallbackContext):
    """Handles the selection of a resource and presents further actions."""
    query: CallbackQuery = update.callback_query
    user_telegram_id = query.from_user.id

    logging.info(f"📥 Received resource selection query: {query.data}")

    # ✅ Extract and ensure `resource_id` is an integer
    if query.data.startswith("view_resource_"):
        try:
            resource_id = int(query.data.replace("view_resource_", ""))
            logging.info(f"✅ Extracted Resource ID: {resource_id}")
        except ValueError:
            logging.error("❌ Invalid resource ID format.")
            await query.answer("❌ Invalid resource ID format.")
            return
    else:
        logging.error("❌ Invalid request format received.")
        await query.answer("❌ Invalid request format.")
        return

    # ✅ Fetch user ID from Supabase
    user_data = supabase_client.table("users") \
        .select("id") \
        .eq("telegram_id", user_telegram_id) \
        .execute()

    if not user_data.data:
        await query.answer("❌ User not found.")
        return

    user_id = user_data.data[0]["id"]

    # ✅ Fetch the resource details
    resource = supabase_client.table("resources") \
        .select("id, title, url, summary") \
        .eq("id", resource_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()

    logging.info(f"📖 Retrieved resource: {resource}")

    if not resource.data:
        await query.answer("❌ Resource not found.")
        return

    # ✅ Mark the resource as viewed
    supabase_client.table("resources").update({"is_viewed": True}) \
        .eq("id", resource_id) \
        .execute()

    # ✅ Create action buttons
    keyboard = [
        [InlineKeyboardButton("📜 Get TL;DR", callback_data=f"get_tldr_{resource_id}")],
        [InlineKeyboardButton("📄 View PDF", callback_data=f"view_pdf_{resource_id}")],
        [InlineKeyboardButton("🔗 Explore Related Topics", callback_data=f"explore_topics_{resource_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"📖 **{resource.data['title']}**\n🔗 [{resource.data['url']}]({resource.data['url']})\n\n"
    message += "What would you like to do next? 👇"

    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    await query.answer()


# ✅ Function to handle user clicking "Get TL;DR"
async def handle_tldr_request(update: Update, context: CallbackContext):
    """Sends a TL;DR of the selected resource."""
    query: CallbackQuery = update.callback_query
    resource_id = query.data.replace("get_tldr_", "")

    # ✅ Fetch TL;DR from Supabase
    resource = supabase_client.table("resources") \
        .select("summary") \
        .eq("id", resource_id) \
        .single() \
        .execute()

    if not resource.data:
        await query.answer("❌ TL;DR not available.")
        return

    message = f"📜 **TL;DR:**\n{resource.data['summary']}"
    await query.message.reply_text(message, parse_mode="Markdown")
    await query.answer()


from telegram import CallbackQuery

async def handle_pdf_request(update: Update, context: CallbackContext):
    """Handles a user's request to view a PDF of the enriched resource."""
    query: CallbackQuery = update.callback_query
    user_telegram_id = query.from_user.id

    logging.info(f"📥 Received PDF request. Query Data: {query.data}")

    # ✅ Extract and Convert resource_id to an integer
    if query.data.startswith("view_pdf_"):
        try:
            resource_id = int(query.data.replace("view_pdf_", ""))
            logging.info(f"✅ Extracted Resource ID: {resource_id}")
        except ValueError:
            logging.error("❌ Invalid resource ID format.")
            await query.answer("❌ Invalid resource ID format.")
            return
    else:
        logging.error("❌ Invalid request format received.")
        await query.answer("❌ Invalid request format.")
        return

    # ✅ Fetch user ID from Supabase
    try:
        user_data = supabase_client.table("users") \
            .select("id") \
            .eq("telegram_id", user_telegram_id) \
            .execute()

        if not user_data.data:
            logging.error("❌ User not found in the database.")
            await query.answer("❌ User not found.")
            return

        user_id = user_data.data[0]["id"]
        logging.info(f"✅ User ID: {user_id}")

    except Exception as e:
        logging.error(f"❌ Supabase query error (user lookup): {e}")
        await query.answer("❌ Internal error. Please try again.")
        return

    # ✅ Fetch PDF URL from Supabase
    try:
        resource = supabase_client.table("resources") \
            .select("pdf_url") \
            .eq("id", resource_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if resource.data and resource.data.get("pdf_url"):
            pdf_url = resource.data["pdf_url"]
            logging.info(f"📄 PDF already exists: {pdf_url}")

            await query.message.reply_text(
                f"📄 Your learning resource is ready! [Download PDF]({pdf_url})",
                parse_mode="Markdown"
            )
            await query.answer()
            return  # ✅ Exit early since PDF is already available
        else:
            logging.info("⚠️ PDF not found. Proceeding with generation.")

    except Exception as e:
        logging.error(f"❌ Supabase query error (PDF lookup): {e}")
        await query.answer("❌ Error retrieving PDF. Please try again.")
        return

    # ✅ Fetch enrichment data for the resource
    try:
        enrichment_data = supabase_client.table("ai_enrichments") \
            .select("*") \
            .eq("resource_id", resource_id) \
            .single() \
            .execute()

        if not enrichment_data.data:
            logging.error("❌ No enrichment data found. Cannot generate PDF.")
            await query.answer("❌ No enrichment data found. Cannot generate PDF.")
            return

        dynamic_enriched_content = json.loads(enrichment_data.data.get("dynamic_enrichment_data"))
        logging.info(f"✅ Enrichment data found for Resource ID: {resource_id}")

    except Exception as e:
        logging.error(f"❌ Supabase query error (enrichment lookup): {e}")
        await query.answer("❌ Error retrieving enrichment data. Please try again.")
        return

    # ✅ Generate PDF
    try:
        logging.info(f"DYNAMIC ENRICHED CONTENT", dynamic_enriched_content)
        logging.info(f"📝 Generating PDF for Resource ID: {resource_id}")
        pdf_buffer = generate_pdf(user_id, resource_id, dynamic_enriched_content)
        logging.info("✅ PDF successfully generated.")

    except Exception as e:
        logging.error(f"❌ PDF generation error: {e}")
        await query.answer("❌ Failed to generate PDF.")
        return

    # ✅ Upload PDF to Supabase
    try:
        logging.info(f"📤 Uploading PDF for Resource ID: {resource_id}")
        pdf_url = upload_pdf_to_supabase(user_id, resource_id, pdf_buffer)
        # pdf_url = save_pdf_locally(user_id, resource_id, pdf_buffer)

        # ✅ Store the new URL in the database
        supabase_client.table("resources") \
            .update({"pdf_url": pdf_url}) \
            .eq("id", resource_id) \
            .execute()

        logging.info(f"✅ PDF uploaded successfully: {pdf_url}")

        await query.message.reply_text(
            f"📄 Your learning resource is ready! [Download PDF]({pdf_url})",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"❌ Error uploading PDF to Supabase: {e}")
        await query.answer("❌ Failed to upload PDF.")
        return

    await query.answer()  # ✅ Closes the button interaction


# ✅ Function to handle user clicking "Explore Related Topics"
async def handle_explore_topics(update: Update, context: CallbackContext):
    """Fetches related topics based on enrichment."""
    query: CallbackQuery = update.callback_query
    # resource_id = query.data.replace("explore_topics_", "")

    # # ✅ Fetch Related Concepts from Supabase
    # resource = supabase_client.table("resources") \
    #     .select("enriched_data") \
    #     .eq("id", resource_id) \
    #     .single() \
    #     .execute()

    # if not resource.data or not resource.data["enriched_data"]:
    #     await query.answer("❌ No related topics found.")
    #     return

    # enriched_data = resource.data["enriched_data"]
    # related_concepts = enriched_data.get("related_concepts", [])

    # if not related_concepts:
    #     await query.answer("❌ No related topics found.")
    #     return

    # message = "🔗 **Explore Related Topics:**\n"
    # for concept in related_concepts:
    #     message += f"• {concept}\n"

    # await query.message.reply_text(message, parse_mode="Markdown")
    await query.answer("❌ No related topics found.")
    await query.answer()

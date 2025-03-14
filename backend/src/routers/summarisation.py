# ✅ Summarize a link
@app.post("/summarise_link")
async def summarise_link(data: schemas.SummariseLinkRequest):
    url = extract_url(data.message)
    if not url:
        return HTTPException(status_code=400, detail="No valid URL found")

    diffbot_response = requests.get(f"https://api.diffbot.com/v3/analyze?url={quote(url)}&token={DIFFBOT_TOKEN}")
    extracted_text = extract_diffbot_text(diffbot_response.json())

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Summarize the following text."}, {"role": "user", "content": extracted_text}],
    )

    summary = response.choices[0].message.content
    bot.send_telegram_message(data.user_id, f"📚 **Summary:**\n\n{summary}")

    return {"extracted_url": url, "diffbot_summary": extracted_text}




from src.config.settings import openai_client, supabase_client

async def generate_summary(content: str) -> str:
    """
    Generates a summary of the provided content using OpenAI's GPT-4 model.
    
    :param content: The content to summarize.
    :return: The generated summary.
    """
    # Initialize the OpenAI client
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": f"Summarize the following content: {content}"}
        ],
        max_tokens=150,
        temperature=0.7,
    )

    summary = response.choices[0].message.content


    return summary
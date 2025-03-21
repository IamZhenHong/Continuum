import os
from dotenv import load_dotenv
from openai import OpenAI
import logging
from pydantic import BaseModel, Field, Extra
from typing import List, Optional, Dict, Any


# ✅ Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dynamic-enrichment")

# ✅ Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

import json
from typing import Union

class DynamicEnrichmentSchema(BaseModel):
    """
    A flexible schema that accepts any dynamic keys returned from enrichment.
    """
    main_concept: Optional[str] = Field(None, description="The core idea or theme")
    
    # Other possible common fields
    key_points: Optional[List[str]] = None
    actionable_takeaways: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None
    related_topics: Optional[List[str]] = None

    # Catch-all for dynamically introduced keys
    additional_fields: Dict[str, Any] = {}

    class Config:
        extra = Extra.allow  # allow fields not explicitly declared
        arbitrary_types_allowed = True

    def __init__(self, **data):
        known_fields = self.__fields__.keys()
        dynamic_fields = {k: v for k, v in data.items() if k not in known_fields}
        super().__init__(**data)
        self.additional_fields = dynamic_fields

def parse_enrichment_response(raw_json: Union[str, dict]) -> DynamicEnrichmentSchema:
    """
    Parse raw enrichment JSON into a DynamicEnrichmentSchema.

    Args:
        raw_json (str | dict): The raw JSON string or dict from GPT.

    Returns:
        DynamicEnrichmentSchema: Pydantic model with both known and custom fields.
    """
    if isinstance(raw_json, str):
        # 🧼 Clean Markdown-style code block
        raw_json = raw_json.strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json.replace("```json", "").strip()
        if raw_json.endswith("```"):
            raw_json = raw_json[:-3].strip()

        try:
            raw_json = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Decode Error: {e}")
            logger.error(f"🧪 Raw received string:\n{raw_json}")
            raise ValueError("Failed to decode enrichment response as JSON")

    return DynamicEnrichmentSchema(**raw_json)


def generate_dynamic_schema(resource_type: str, user_instruction: str, content: str) -> dict:
    """
    Generate enrichment schema based on resource type and user instruction.
    
    Args:
        resource_type (str): Type of resource (e.g. "insight", "opinion", "knowledge").
        user_instruction (str): Custom user instruction (e.g. "Focus on applicable strategies").
        content (str): Raw content of the resource.
        
    Returns:
        dict: Enriched structured response.
    """
    logger.info("💡 Generating dynamic enrichment based on context...")

    prompt = f"""
You are an intelligent enrichment engine that dynamically creates a tailored schema
based on the *type* of resource and the *user's instruction*.

Your job is to:
1. Understand the nature of the content (e.g. insight vs opinion vs knowledge).
2. Understand what the user wants (from the instruction).
3. Adapt the **fields** and **focus** of the enrichment accordingly.

## Resource Type:
{resource_type}

## User Instruction:
{user_instruction}

## Content:
{content}

📌 Return a **JSON** object with customized fields. Use clear keys.
You may introduce new keys that are relevant to the type or instruction (e.g. "contrarian view", "supporting evidence", "applications", "warnings", etc.).

ONLY return valid JSON. DO NOT include explanation or Markdown.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that adapts enrichment schemas dynamically."},
            {"role": "user", "content": prompt}
        ]
    )

    try:
        raw = response.choices[0].message.content
        logger.info("✅ Enrichment generated successfully!")
        print("\n🧠 Enriched Output:\n", raw)
        return raw
    except Exception as e:
        logger.error(f"❌ Error parsing OpenAI response: {e}")
        return {}


# ✅ Example run
if __name__ == "__main__":
    example_resource_type = "insight"
    example_user_instruction = "Focus on the key business takeaways for a startup founder"
    example_content = """
In this article, the author reflects on their startup journey and how they pivoted by listening to customer feedback. 
They emphasize that founders often fall in love with their ideas and forget to validate with real demand. The piece ends with 
an actionable reminder: 'Let the market pull you — don’t push your vision blindly.'
    """

    enrichment_raw =generate_dynamic_schema(
        resource_type=example_resource_type,
        user_instruction=example_user_instruction,
        content=example_content
    )


    parsed_schema = parse_enrichment_response(enrichment_raw)

    print("🎯 Main Concept:", parsed_schema.main_concept)
    print("🧩 Dynamic Fields:", parsed_schema.additional_fields)

import os
from dotenv import load_dotenv
from openai import OpenAI
import logging
from pydantic import BaseModel, Field, Extra
from typing import List, Optional, Dict, Any
from src.config.settings import supabase_client, redis_client, openai_client


# ✅ Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dynamic-enrichment")


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

from pydantic import create_model

from typing import get_args, get_origin
from pydantic import create_model
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Union

def infer_pydantic_type(value: Any):
    """
    Map Python values to appropriate Pydantic/typing types with JSON schema compatibility.
    """
    if isinstance(value, str):
        return (str, Field(default=value))
    elif isinstance(value, bool):
        return (bool, Field(default=value))
    elif isinstance(value, int):
        return (int, Field(default=value))
    elif isinstance(value, float):
        return (float, Field(default=value))
    elif isinstance(value, list):
        # Handle homogeneous list types (assume list of str/int/dict for now)
        if not value:
            return (List[Any], Field(default=value))
        first_type = type(value[0])
        if all(isinstance(i, first_type) for i in value):
            inner_type = infer_pydantic_type(value[0])[0]
            return (List[inner_type], Field(default=value))
        else:
            return (List[Any], Field(default=value))
    elif isinstance(value, dict):
        return (Dict[str, Any], Field(default=value))
    else:
        return (Any, Field(default=value))
    
def parse_enrichment_response(raw_json: Union[str, dict]) -> BaseModel:
    """
    Parses raw GPT JSON and dynamically generates a structured Pydantic model.
    The resulting model is usable as a schema in OpenAI's response_format.

    Args:
        raw_json (str | dict): Raw JSON from GPT.

    Returns:
        BaseModel: A Pydantic model instance with structured fields.
    """
    if isinstance(raw_json, str):
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

    # ❗️ Remove default values when creating schema
    fields = {
        k: (type(v), ...) for k, v in raw_json.items()
    }

    StructuredModel = create_model("StructuredEnrichment", **fields)
    return StructuredModel


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
You are an intelligent enrichment engine that dynamically creates a tailored JSON schema
based on the *type* of resource and the *user's instruction*.

Your responsibilities:
1. Analyze the resource type to guide what fields should be included (e.g., insight, opinion, or knowledge).
2. Adapt your enrichment to follow the user's instruction (e.g., emphasize strategies, applications, context, etc.).
3. Dynamically select relevant fields such as:
   - summary
   - actionable_insights
   - applications
   - supporting_evidence
   - risks or warnings
   - contrarian_view
   - additional_reading
   - context
   - etc.

🚨 Required:
- You **must always** include a field called `"sources"` that lists relevant URLs or source links used or referenced (even if only from the input content).
- The `sources` key should be at the **bottom** of the object and contain a list of strings (URLs).
- If there are no actual URLs in the content, include `"sources": ["No specific source provided"]`.

---

## Resource Type:
{resource_type}

## User Instruction:
{user_instruction}

## Content:
{content}

Return:
- A **valid JSON object only**.
- No markdown, no explanation, no code blocks.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that adapts enrichment schemas dynamically and always includes source links."},
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

# # ✅ Example run
# if __name__ == "__main__":
#     example_resource_type = "insight"
#     example_user_instruction = "Focus on the key business takeaways for a startup founder"
#     example_content = """
# In this article, the author reflects on their startup journey and how they pivoted by listening to customer feedback. 
# They emphasize that founders often fall in love with their ideas and forget to validate with real demand. The piece ends with 
# an actionable reminder: 'Let the market pull you — don’t push your vision blindly.'
#     """

#     enrichment_raw =generate_dynamic_schema(
#         resource_type=example_resource_type,
#         user_instruction=example_user_instruction,
#         content=example_content
#     )


#     parsed_schema = parse_enrichment_response(enrichment_raw)

#     print("🎯 Main Concept:", parsed_schema.main_concept)
#     print("🧩 Dynamic Fields:", parsed_schema.additional_fields)

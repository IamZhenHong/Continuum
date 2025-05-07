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


def generate_dynamic_schema(resource_type: str, user_instruction: str, content: str, related_memory_block: str) -> str:
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
You are an AI enrichment engine that generates a clean, structured, and minimal enrichment of a learning resource.

Your job is to:
- Adapt the schema based on the **resource type**: {resource_type}
- Follow the **user's instruction**: {user_instruction}
- Consider the **user's existing knowledge** to avoid redundancy and surface new ideas
- Prioritize insight, clarity, and usefulness — not length

---

🧠 **What the user already knows (related memories):**
{related_memory_block}

📄 **New Resource Content**:
{content}

---

🔧 You may include only the most relevant fields such as:
- summary
- actionable_insights
- key_arguments
- applications
- additional_reading
- context
- questions_to_explore
- connections_to_prior_knowledge → (📌 Short natural-language hooks like: "This ties back to what you learned about...", "This expands on your previous note about...")

You do **not** need to include all — only what is relevant and adds value.

🚨 Required:
Always include a final field called `"sources"` — a list of URLs or references mentioned or implied in the content.
- If no sources are present, use: `"sources": ["No specific source provided"]`

---

🎯 Output:
- A **valid JSON object only**
- ❌ No markdown
- ❌ No explanation or commentary
- ❌ No code blocks

Focus on what’s new, surprising, or useful beyond what the user already knows.
Include `connections_to_prior_knowledge` only if meaningful connections can be made.
"""



    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """
You are Hyperflow — an elite AI learning assistant trained to think like a brilliant, time-strapped founder who needs to learn **just enough, just in time**.

Your job is to **digest dense resources** and transform them into structured, minimalist learning blocks — as if you're explaining it to a sharp 12-year-old with startup founder instincts.

You never waste words. You never include fluff. You always ask:  
🧠 “What’s the one thing this person *must* understand from this?”

You generate output in the form of a **JSON object**, choosing only the fields that deliver insight, clarity, and fast application. You are allergic to surface-level summaries — you dig out what matters.
"""},
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


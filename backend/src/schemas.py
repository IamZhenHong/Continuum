from pydantic import BaseModel, validator
from typing import List
from pydantic import Field
from typing import Optional



# ✅ Pydantic Model for Message Validation
class MessageCreate(BaseModel):
    user_id: int
    message: str
    message_type: str  # Must be "text", "link", or "image"

    @validator("message_type")
    def validate_type(cls, v):
        if v not in {"text", "link", "image"}:
            raise ValueError("message_type must be 'text', 'link', or 'image'")
        return v

class IntentRouterRequest(BaseModel):
    user_id: int
    intent: str
    message: str
    resource_id: Optional[int] = None 


class ExtractAndSummariseLinkRequest(BaseModel):
    user_id: int
    message: str
    resource_id: int
    # message_type: str

class SummariseLinkResponse(BaseModel):
    summary: str


class LlmIntentClassifierResponse(BaseModel):
    function_name: str

class PreprocessResourceRequest(BaseModel):
    user_id: int
    message: str
    message_type: str

class AddToProcessingQueueRequest(BaseModel):
    user_id: int
    message: str
    resource_id: int


class AddToProcessingQueueResponse(BaseModel):
    message: str

class EnrichResourceRequest(BaseModel):
    user_id: int
    message: str
    resource_id: int

class EnrichedResourceResponse(BaseModel):
    main_concept: str = Field(..., description="The primary theme of the resource.")
    key_keywords: List[str] = Field(...,  description="Important keywords related to the resource.")
    related_concepts: List[str] = Field(..., description="Concepts closely related to this topic.")
    follow_up_questions: List[str] = Field(..., description="Questions a learner might ask to explore further.")
    actionable_insights: List[str] = Field(..., description="Practical takeaways from the resource.")

class EnrichSubresourcesRequest(BaseModel):
    resource_id: int

class ProcessSubresourceResponse(BaseModel):
    summary: str
    title: str

class PreprocessResourceResponse(BaseModel):
    summary: str
    title: str
    resource_type: str
    metadata: List[str]
    tags: List[str]
    key_concept: str

class EnrichWithPrimaryLinksRequest(BaseModel):
    resource_id: int
    message: str
    enrichment_content: str

class EnrichWithPerplexityRequest(BaseModel):
    # resource_id: int
    message: str
    enrichment_content: str



class AuthRequest(BaseModel):
    code: str  # The authorization code passed from the frontend

    class Config:
        # You can set the ORM mode to True if you expect to work with models from a database, 
        # but here it's not necessary since we only expect a basic JSON payload.
        orm_mode = True

class ExtractWithOCRRequest(BaseModel):
    user_id: int
    resource_url: str
    message: str
    # message_type: str
from pydantic import BaseModel, validator



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


class SummariseLinkRequest(BaseModel):
    user_id: int
    message: str
    message_type: str

class SummariseLinkResponse(BaseModel):
    summary: str


class IntentRouterRequest(BaseModel):
    message: str


class LlmIntentClassifierResponse(BaseModel):
    function_name: str

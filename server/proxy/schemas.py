
"""FastAPI 요청/응답 데이터 형식."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list[dict]
    use_tier_routing: bool = False


class ChatResponse(BaseModel):
    content: str


class ChatGuardrailRequest(BaseModel):
    prompt: str


class ChatGuardrailResponse(BaseModel):
    is_appropriate: bool


class DecideRouteRequest(BaseModel):
    prompt: str


class DecideRouteResponse(BaseModel):
    route: str


class ImageGenerationRequest(BaseModel):
    prompt: str


class ImageGenerationResponse(BaseModel):
    image_base64: str
    image_mime_type: str = "image/jpeg"


class ImageAnalysisRequest(BaseModel):
    image_base64: str
    question: str


class ImageAnalysisResponse(BaseModel):
    content: str

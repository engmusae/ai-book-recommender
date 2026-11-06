
"""FastAPI 요청/응답 데이터 형식."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list[dict]
    use_tier_routing: bool = False


class ChatResponse(BaseModel):
    content: str
    # F710: 실제로 답변을 생성한 모델명 (등급 라우팅 결과 확인용)
    model_used: str | None = None


# F709: 텍스트 응답 점수 계산
class ChatScoreRequest(BaseModel):
    messages: list[dict]
    answer: str


class ChatScoreResponse(BaseModel):
    score: int
    reason: str


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


# F711: TTS
class SpeechRequest(BaseModel):
    text: str


class SpeechResponse(BaseModel):
    audio_data: str

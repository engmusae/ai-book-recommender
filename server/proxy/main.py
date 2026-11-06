
"""FastAPI Proxy: Django만 이 서버를 호출하며 GMS_KEY는 이 서버에서만 사용한다."""

import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from schemas import (
    ChatGuardrailRequest,
    ChatGuardrailResponse,
    ChatRequest,
    ChatResponse,
    ChatScoreRequest,
    ChatScoreResponse,
    DecideRouteRequest,
    DecideRouteResponse,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
    SpeechRequest,
    SpeechResponse,
)

# ==================================================
# 환경 변수 및 모델 설정
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GMS_KEY = os.getenv("GMS_KEY", "")

GMS_URL = os.getenv(
    "GMS_URL",
    "https://gms.ssafy.io/gmsapi/api.openai.com/v1",
).rstrip("/")

GMS_INTERACTIONS_URL = (
    "https://gms.ssafy.io/gmsapi/"
    "generativelanguage.googleapis.com/v1beta/interactions"
)

MODEL_NANO = "gpt-5-nano"
MODEL_MINI = "gpt-5-mini"
MODEL_TTS = "gpt-4o-mini-tts"
MODEL_IMAGE = "gemini-3.1-flash-lite-image"

HEADERS = {
    "Authorization": f"Bearer {GMS_KEY}",
}

app = FastAPI(
    title="Book Recommend Proxy (FastAPI)",
    version="1.0.0",
)


# ==================================================
# GMS 공통 요청 함수
# ==================================================

def gms_post(path, payload):
    """OpenAI 호환 GMS API 요청"""

    if not GMS_KEY:
        print("[GMS 설정 오류] GMS_KEY가 설정되지 않았습니다.")

        raise HTTPException(
            status_code=503,
            detail="model server error",
        )

    try:
        response = requests.post(
            f"{GMS_URL}{path}",
            headers=HEADERS,
            json=payload,
            timeout=120,
        )

    except requests.RequestException as exc:
        print("[GMS 연결 실패]", path, str(exc)[:500])

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc

    if response.status_code != 200:
        print(
            "[GMS 호출 실패]",
            path,
            response.status_code,
            response.text[:1000],
        )

        raise HTTPException(
            status_code=503,
            detail="model server error",
        )

    return response


def ask_gms(messages, model=MODEL_NANO, response_format=None):
    """GMS Chat Completions 호출"""

    payload = {
        "model": model,
        "messages": messages,
    }

    if response_format:
        payload["response_format"] = response_format

    response = gms_post(
        "/chat/completions",
        payload,
    )

    try:
        return response.json()["choices"][0]["message"]["content"]

    except (ValueError, KeyError, IndexError, TypeError) as exc:
        print("[GMS 응답 형식 오류]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc


# ==================================================
# Gemini Interactions API
# ==================================================

def ask_gms_interactions(prompt):
    """
    SSAFY GMS Gemini Interactions API 호출

    검증된 호출 방식:
    POST /gmsapi/generativelanguage.googleapis.com/v1beta/interactions

    인증:
    x-goog-api-key
    """

    if not GMS_KEY:
        print("[GMS 설정 오류] GMS_KEY가 설정되지 않았습니다.")

        raise HTTPException(
            status_code=503,
            detail="model server error",
        )

    headers = {
        "x-goog-api-key": GMS_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_IMAGE,
        "input": [
            {
                "type": "text",
                "text": prompt,
            }
        ],
    }

    try:
        response = requests.post(
            GMS_INTERACTIONS_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

    except requests.RequestException as exc:
        print("[GMS Interactions 연결 실패]", str(exc)[:500])

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc

    if response.status_code != 200:
        print(
            "[GMS Interactions 호출 실패]",
            response.status_code,
            response.text[:1000],
        )

        raise HTTPException(
            status_code=503,
            detail="model server error",
        )

    try:
        result = response.json()

    except ValueError as exc:
        print("[GMS Interactions JSON 해석 실패]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc

    if result.get("status") != "completed":
        print(
            "[GMS 이미지 생성 미완료]",
            result.get("status"),
        )

        raise HTTPException(
            status_code=503,
            detail="image generation incomplete",
        )

    # steps 안에서 model_output 단계 탐색
    for step in result.get("steps", []):

        if step.get("type") != "model_output":
            continue

        # model_output의 content에서 이미지 탐색
        for content in step.get("content", []):

            if content.get("type") == "image":

                image_data = content.get("data")

                if not image_data:
                    continue

                return {
                    "image_base64": image_data,
                    "image_mime_type": content.get(
                        "mime_type",
                        "image/jpeg",
                    ),
                }

    print("[GMS 응답 오류] 이미지 데이터를 찾을 수 없습니다.")

    raise HTTPException(
        status_code=503,
        detail="image data not found",
    )


# ==================================================
# JSON Schema 공통 함수
# ==================================================

def json_schema(name, properties):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys()),
                "additionalProperties": False,
            },
        },
    }


# ==================================================
# F703. Guardrail
# ==================================================

GUARDRAIL_PROMPT = """
당신은 도서 추천 서비스의 안전성 검사기다.

사용자 요청이 다음 중 하나를 명백하게 요구할 때만
is_appropriate=false로 판단한다.

1. 폭력, 자해, 혐오 표현 또는 성인 콘텐츠를
   생성하거나 조장해 달라는 요구

2. 명백히 불법인 행위를 실행하는 구체적인 방법이나
   절차를 알려 달라는 요구

3. 다른 사람의 개인정보, 계정 정보 또는 사적인
   식별 정보를 알아내 달라는 요구

문학 작품에 대한 비평, 토론, 역사적 설명,
예방 및 안전 목적의 질문은 그 자체로 부적절하지 않다.

판단이 모호하거나 위 기준에 명백히 해당하지 않으면
반드시 true로 판단한다.

JSON 스키마에 맞는 결과만 반환한다.
"""


@app.post(
    "/api/v1/chat/guardrail",
    response_model=ChatGuardrailResponse,
)
def chat_guardrail(request: ChatGuardrailRequest):

    messages = [
        {
            "role": "developer",
            "content": GUARDRAIL_PROMPT,
        },
        {
            "role": "user",
            "content": request.prompt,
        },
    ]

    response_format = json_schema(
        "guardrail_response",
        {
            "is_appropriate": {
                "type": "boolean",
            }
        },
    )

    answer = ask_gms(
        messages,
        MODEL_NANO,
        response_format,
    )

    try:
        result = json.loads(answer)

        return {
            "is_appropriate": bool(
                result["is_appropriate"]
            )
        }

    except (ValueError, KeyError, TypeError) as exc:
        print("[Guardrail 응답 해석 실패]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc


def ensure_appropriate(prompt):
    """요청의 적절성 검사"""

    result = chat_guardrail(
        ChatGuardrailRequest(prompt=prompt)
    )

    if not result["is_appropriate"]:
        raise HTTPException(
            status_code=403,
            detail="inappropriate request",
        )


# ==================================================
# F710. 모델 등급 라우팅
# ==================================================

TIER_PROMPT = """
당신은 도서 추천 요청의 난이도 분류기다.

사용자 요청을 읽고 "simple" 또는 "complex" 중 하나로 분류한다.

1. "simple"
   - 장르나 주제만 간단히 언급한 짧은 요청
   - 예: "소설 추천해줘", "가벼운 에세이 추천"

2. "complex"
   - 분위기, 상황, 감정, 독자 수준, 분량 등
     여러 조건을 함께 제시한 요청
   - 비교, 이유 설명, 맥락 이해가 필요한 요청
   - 예: "비 오는 날 혼자 읽기 좋은, 위로가 되는 짧은 에세이"

판단이 애매하면 "simple"로 분류한다.
JSON 스키마에 맞는 결과만 반환한다.
"""


def decide_model_tier(prompt):
    """요청 난이도를 gpt-5-nano로 판단해 'simple' 또는 'complex'를 반환"""

    messages = [
        {
            "role": "developer",
            "content": TIER_PROMPT,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    response_format = json_schema(
        "tier_response",
        {
            "tier": {
                "type": "string",
                "enum": ["simple", "complex"],
            }
        },
    )

    answer = ask_gms(
        messages,
        MODEL_NANO,
        response_format,
    )

    try:
        tier = json.loads(answer)["tier"]

        if tier not in ("simple", "complex"):
            raise ValueError("unsupported tier")

        return tier

    except (ValueError, KeyError, TypeError) as exc:
        print("[모델 등급 응답 해석 실패]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc


# ==================================================
# F702. 텍스트 추천
# ==================================================

@app.post(
    "/api/v1/chat/completions",
    response_model=ChatResponse,
)
def chat_completions(request: ChatRequest):

    if not request.messages:
        raise HTTPException(
            status_code=422,
            detail="messages must not be empty",
        )

    user_text = str(
        request.messages[-1].get("content", "")
    )

    ensure_appropriate(user_text)

    # F710: 등급 라우팅을 켠 경우에만 난이도에 따라 모델을 선택
    model = MODEL_NANO

    if request.use_tier_routing:
        tier = decide_model_tier(user_text)

        if tier == "complex":
            model = MODEL_MINI

    content = ask_gms(
        request.messages,
        model,
    )

    return {
        "content": content,
        "model_used": model,
    }


# ==================================================
# F709. 텍스트 응답 점수 계산
# ==================================================

SCORE_PROMPT = """
당신은 도서 추천 답변의 품질 평가자다.

[사용자 요청]과 [AI 답변]을 보고, 답변이 사용자의 취향과
요청 조건에 얼마나 적합한지 0~100점의 정수로 평가한다.

평가 기준:
- 요청한 조건(장르, 분위기, 분량 등)을 반영했는가
- 추천 도서와 추천 이유가 구체적인가
- 요청과 관련 없는 내용이 섞여 있지 않은가

reason에는 점수의 근거를 한국어 1~2문장으로 간단히 적는다.
JSON 스키마에 맞는 결과만 반환한다.
"""


@app.post(
    "/api/v1/chat/score",
    response_model=ChatScoreResponse,
)
def chat_score(request: ChatScoreRequest):

    if not request.messages:
        raise HTTPException(
            status_code=422,
            detail="messages must not be empty",
        )

    user_text = str(
        request.messages[-1].get("content", "")
    )

    messages = [
        {
            "role": "developer",
            "content": SCORE_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"[사용자 요청]\n{user_text}\n\n"
                f"[AI 답변]\n{request.answer}"
            ),
        },
    ]

    response_format = json_schema(
        "score_response",
        {
            "score": {
                "type": "integer",
            },
            "reason": {
                "type": "string",
            },
        },
    )

    answer = ask_gms(
        messages,
        MODEL_NANO,
        response_format,
    )

    try:
        result = json.loads(answer)

        # strict 스키마는 min/max를 지원하지 않으므로 직접 0~100으로 제한
        score = max(0, min(100, int(result["score"])))

        return {
            "score": score,
            "reason": str(result["reason"]),
        }

    except (ValueError, KeyError, TypeError) as exc:
        print("[점수 응답 해석 실패]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc


# ==================================================
# F704. 라우트 결정
# ==================================================

ROUTE_PROMPT = """
당신은 도서 추천 서비스의 요청 라우터다.

사용자가 원하는 최종 결과가 텍스트 답변인지,
실제 책 표지 이미지인지 판단한다.

1. 실제 이미지 생성 요청이면
   "/images/generations"를 선택한다.

   - 책 표지, 소설 표지, 북커버, 도서 커버,
     표지 일러스트를 만들어 달라는 요청
   - 표지에 들어갈 장면이나 그림을 묘사한 요청
   - 완성할 이미지의 장면과 용도를 설명하는 문장

2. 텍스트 답변 요청이면
   "/chat/completions"를 선택한다.

   - 책이나 작품 추천
   - 줄거리 및 감상 설명
   - 독서 취향 상담
   - 표지 디자인 아이디어나 제작 방법 설명

3. 사용자가 원하는 결과물을 기준으로 판단한다.

4. 반드시 다음 두 경로 중 하나만 반환한다.

   "/chat/completions"
   "/images/generations"
"""


@app.post(
    "/api/v1/decide-route",
    response_model=DecideRouteResponse,
)
def decide_route(request: DecideRouteRequest):

    messages = [
        {
            "role": "developer",
            "content": ROUTE_PROMPT,
        },
        {
            "role": "user",
            "content": request.prompt,
        },
    ]

    response_format = json_schema(
        "route_response",
        {
            "route": {
                "type": "string",
                "enum": [
                    "/chat/completions",
                    "/images/generations",
                ],
            }
        },
    )

    answer = ask_gms(
        messages,
        MODEL_NANO,
        response_format,
    )

    try:
        result = json.loads(answer)
        route = result["route"]

        if route not in (
            "/chat/completions",
            "/images/generations",
        ):
            raise ValueError("unsupported route")

        return {
            "route": route,
        }

    except (ValueError, KeyError, TypeError) as exc:
        print("[라우트 응답 해석 실패]", str(exc))

        raise HTTPException(
            status_code=503,
            detail="model server error",
        ) from exc


# ==================================================
# F705. 이미지 생성
# ==================================================

@app.post(
    "/api/v1/images/generations",
    response_model=ImageGenerationResponse,
)
def image_generations(request: ImageGenerationRequest):

    # 이미지 생성 전 Guardrail 검사
    ensure_appropriate(request.prompt)

    # Gemini Interactions API로 이미지 생성
    result = ask_gms_interactions(
        request.prompt
    )

    return result


# ==================================================
# F707. 이미지 분석
# ==================================================

ANALYSIS_PROMPT = """
당신은 책 표지 분석 전문가다.

제공된 책 표지를 시각적으로 살펴보고
다음 순서로 한국어로 답한다.

1. 표지에서 읽을 수 있는 제목과 저자
   (확실하지 않으면 추정이라고 표시)

2. 표지 디자인과 단서를 바탕으로 추정한 장르 및 분위기

3. 표지와 주제 및 분위기가 비슷한 실제 도서
   2~3권과 추천 이유

이미지에서 확인할 수 없는 정보를
사실처럼 단정하지 않는다.
"""


@app.post(
    "/api/v1/images/analysis",
    response_model=ImageAnalysisResponse,
)
def image_analysis(request: ImageAnalysisRequest):

    # 이미지 분석 전 Guardrail 검사
    ensure_appropriate(request.question)

    # 기존 OpenAI 호환 멀티모달 Chat Completions 방식 유지
    image_url = (
        f"data:image/png;base64,{request.image_base64}"
    )

    user_content = [
        {
            "type": "image_url",
            "image_url": {
                "url": image_url,
            },
        },
        {
            "type": "text",
            "text": request.question,
        },
    ]

    messages = [
        {
            "role": "developer",
            "content": ANALYSIS_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]

    content = ask_gms(
        messages,
        MODEL_NANO,
    )

    return {
        "content": content,
    }


# ==================================================
# F711. TTS
# ==================================================

@app.post(
    "/api/v1/generate-speech",
    response_model=SpeechResponse,
)
def generate_speech(request: SpeechRequest):

    if not request.text.strip():
        raise HTTPException(
            status_code=422,
            detail="text must not be empty",
        )

    response = gms_post(
        "/audio/speech",
        {
            "model": MODEL_TTS,
            "input": request.text,
            "voice": "nova",
            "response_format": "mp3",
        },
    )

    if not response.content:
        print("[TTS 응답 오류] 오디오 데이터가 비어 있습니다.")

        raise HTTPException(
            status_code=503,
            detail="model server error",
        )

    return {
        "audio_data": base64.b64encode(
            response.content
        ).decode("utf-8"),
    }

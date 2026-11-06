
import base64
import requests

from django.conf import settings
from django.shortcuts import render, redirect

from .forms import RecommendationForm, ImageUploadForm
from .models import Recommendation


def _proxy_post(endpoint, payload):
    """Django에서 FastAPI로 요청한다."""
    return requests.post(
        f"{settings.PROXY_BASE_URL}{endpoint}",
        json=payload,
        timeout=180,
    )


def _error_response(request, status_code=None, detail=None):
    return render(
        request,
        "recommend/error.html",
        {"status_code": status_code, "detail": detail},
        status=502 if status_code is None else status_code,
    )


def _page_title(mode):
    """상단 메뉴 mode 값에 맞는 화면 제목을 반환한다."""
    return {
        "validation": "입력 검증",
        "text": "텍스트 추천",
        "route": "라우트 결정",
        "image": "이미지 생성",
        "analysis": "이미지 분석",
        "control": "API 흐름 제어",
    }.get(mode, "입력 검증")


def recommend_form(request):
    """F701: ModelForm 입력 검증 및 메뉴별 입력 화면 표시."""

    mode = request.GET.get("mode", "validation")
    page_title = _page_title(mode)

    if request.method == "POST":
        form = RecommendationForm(request.POST)

        if form.is_valid():
            recommendation = form.save()

            return render(
                request,
                "recommend/input_form.html",
                {
                    "form": form,
                    "saved": True,
                    "recommendation": recommendation,
                    "page_title": page_title,
                    "mode": mode,
                },
            )

    else:
        form = RecommendationForm()

    return render(
        request,
        "recommend/input_form.html",
        {
            "form": form,
            "page_title": page_title,
            "mode": mode,
        },
    )


def recommend_flow(request):
    """F704 라우트 결정과 F708 실제 추천 흐름을 처리한다."""

    if request.method != "POST":
        return redirect("recommend:input")

    mode = request.POST.get("mode", "text")
    page_title = _page_title(mode)

    form = RecommendationForm(request.POST)

    if not form.is_valid():
        return render(
            request,
            "recommend/input_form.html",
            {
                "form": form,
                "page_title": page_title,
                "mode": mode,
            },
        )

    recommendation = form.save()
    prompt = recommendation.request_text

    try:
        # F704: 사용자 요청의 유형을 먼저 판단한다.
        route_response = _proxy_post(
            "/decide-route",
            {"prompt": prompt},
        )

        if route_response.status_code == 403:
            return render(
                request,
                "recommend/rejected.html",
                status=403,
            )

        if route_response.status_code != 200:
            return _error_response(
                request,
                route_response.status_code,
                route_response.text[:300],
            )

        route = route_response.json().get("route")

        allowed_routes = (
            "/chat/completions",
            "/images/generations",
        )

        if route not in allowed_routes:
            return _error_response(
                request,
                502,
                "라우트 결정 API가 올바르지 않은 route를 반환했습니다.",
            )

        # F704: 라우트 결정 메뉴에서는 판단 결과만 표시한다.
        # 기존 form을 그대로 전달해 입력값을 유지한다.
        if mode == "route":
            return render(
                request,
                "recommend/input_form.html",
                {
                    "form": form,
                    "page_title": page_title,
                    "mode": mode,
                    "saved": True,
                    "recommendation": recommendation,
                    "route_result": route,
                },
            )

        # F708: 텍스트 추천 API 호출
        if route == "/chat/completions":

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            }

            response = _proxy_post(
                "/chat/completions",
                payload,
            )

            if response.status_code == 403:
                return render(
                    request,
                    "recommend/rejected.html",
                    status=403,
                )

            if response.status_code != 200:
                return _error_response(
                    request,
                    response.status_code,
                    response.text[:300],
                )

            result = response.json()

            return render(
                request,
                "recommend/recommend_flow.html",
                {
                    "result_text": result.get("content", ""),
                    "recommendation": recommendation,
                    "result_type": "text",
                    "route": route,
                },
            )

        # F708: 이미지 생성 API 호출
        response = _proxy_post(
            "/images/generations",
            {"prompt": prompt},
        )

        if response.status_code == 403:
            return render(
                request,
                "recommend/rejected.html",
                status=403,
            )

        if response.status_code != 200:
            return _error_response(
                request,
                response.status_code,
                response.text[:300],
            )

        image_result = response.json()

        return render(
            request,
            "recommend/recommend_flow.html",
            {
                "image_base64": image_result.get("image_base64", ""),
                "image_mime_type": image_result.get(
                    "image_mime_type",
                    "image/png",
                ),
                "recommendation": recommendation,
                "result_type": "image",
                "route": route,
            },
        )

    except (requests.RequestException, ValueError) as exc:
        return _error_response(
            request,
            None,
            str(exc),
        )


def image_analysis(request):
    """F707: 업로드 이미지를 Base64로 변환해 FastAPI에 전달한다."""

    if request.method == "POST":
        form = ImageUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded = form.cleaned_data["image"]

            image_base64 = base64.b64encode(
                uploaded.read()
            ).decode("utf-8")

            payload = {
                "image_base64": image_base64,
                "question": form.cleaned_data["question"],
            }

            try:
                response = _proxy_post(
                    "/images/analysis",
                    payload,
                )

                if response.status_code == 403:
                    return render(
                        request,
                        "recommend/rejected.html",
                        status=403,
                    )

                if response.status_code != 200:
                    return _error_response(
                        request,
                        response.status_code,
                        response.text[:300],
                    )

                return render(
                    request,
                    "recommend/result_text.html",
                    {
                        "content": response.json().get("content", ""),
                        "image_data_uri": (
                            f"data:{uploaded.content_type or 'image/jpeg'};"
                            f"base64,{image_base64}"
                        ),
                        "question": form.cleaned_data["question"],
                        "title": "책 표지 분석 결과",
                    },
                )

            except (requests.RequestException, ValueError) as exc:
                return _error_response(
                    request,
                    None,
                    str(exc),
                )

    else:
        form = ImageUploadForm()

    return render(
        request,
        "recommend/upload_form.html",
        {"form": form},
    )

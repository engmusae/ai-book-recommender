from django import forms

from .models import Recommendation, Speech


class RecommendationForm(forms.ModelForm):
    request_text = forms.CharField(
        label="도서 취향 및 요청",
        max_length=300,
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "maxlength": 300,
            "placeholder": "예) 출퇴근길에 가볍게 읽을 성장 소설을 추천해줘",
            "aria-describedby": "request-help",
        }),
    )

    class Meta:
        model = Recommendation
        fields = ["request_text"]


class ImageUploadForm(forms.Form):
    image = forms.ImageField(label="책 표지 이미지")
    question = forms.CharField(
        label="분석 요청",
        max_length=300,
        required=True,
        initial="이 책 표지를 보고 제목·장르를 추정하고 비슷한 도서를 추천해 주세요.",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 300}),
    )


class SpeechForm(forms.ModelForm):
    """F711: 음성으로 변환할 텍스트 입력."""

    text = forms.CharField(
        label="음성으로 변환할 텍스트",
        max_length=4000,
        required=True,
        widget=forms.Textarea(attrs={
            "rows": 5,
            "maxlength": 4000,
            "placeholder": "예) 출퇴근길에는 데미안을 추천합니다. 짧고 깊은 성장 소설입니다.",
        }),
    )

    class Meta:
        model = Speech
        fields = ["text"]

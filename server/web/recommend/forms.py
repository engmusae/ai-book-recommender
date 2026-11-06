from django import forms

from .models import Recommendation


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

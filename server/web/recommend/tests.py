from django.test import TestCase
from django.urls import reverse
from .forms import RecommendationForm
from .models import Recommendation


class RecommendationFormTests(TestCase):
    def test_empty_request_is_invalid(self):
        self.assertFalse(RecommendationForm(data={"request_text": ""}).is_valid())

    def test_over_300_characters_is_invalid(self):
        self.assertFalse(RecommendationForm(data={"request_text": "가" * 301}).is_valid())

    def test_valid_request_is_saved(self):
        form = RecommendationForm(data={"request_text": "따뜻한 성장 소설 추천"})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Recommendation.objects.count(), 1)


class RecommendationPageTests(TestCase):
    def test_input_page(self):
        response = self.client.get(reverse("recommend:input"))
        self.assertEqual(response.status_code, 200)

    def test_upload_page(self):
        response = self.client.get(reverse("recommend:upload"))
        self.assertEqual(response.status_code, 200)

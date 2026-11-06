from django.db import models


class Recommendation(models.Model):
    request_text = models.TextField(max_length=300)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    image = models.ImageField(upload_to="images/", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.request_text[:50]

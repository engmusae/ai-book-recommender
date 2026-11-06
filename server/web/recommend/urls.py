from django.urls import path
from . import views

app_name = "recommend"

urlpatterns = [
    path("", views.recommend_form, name="input"),
    path("flow/", views.recommend_flow, name="flow"),
    path("upload/", views.image_analysis, name="upload"),
]

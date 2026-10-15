from django.urls import path
from api.views import analyze, health

urlpatterns = [
    path("api/analyze/", analyze),
    path("api/health/", health),
]

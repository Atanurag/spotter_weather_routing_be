from os import read

from django.urls import path
from api.views import analyze, health, alert_test, save_push_subscription, send_test_notification_view
# from api.utils import send_test_notification
urlpatterns = [
    path("api/analyze/", analyze),
    path("api/health/", health),
    path("api/save-subscription/", save_push_subscription),
    # path("api/send/", send_test_notification),
    path('api/send/', send_test_notification_view),
    # path('api/mark-read/<str:notif_id>/', mark_notification_read),

]

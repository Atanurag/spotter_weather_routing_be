from django.db import models

class PushSubscription(models.Model):
    user_id_str = models.CharField(max_length=100, default="user_1")
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


# class NotificationLog(models.Model):
#     user_id_str = models.CharField(max_length=255)
#     notification_id = models.CharField(max_length=255, unique=True)
#     title = models.CharField(max_length=255)
#     is_read = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
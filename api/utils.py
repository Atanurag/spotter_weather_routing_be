import json
from pywebpush import webpush, WebPushException
from django.conf import settings
from .models import PushSubscription

def send_test_notification():
    subscriptions = PushSubscription.objects.filter(user_id_str='user_1')
    
    message_payload = {
        "title": "push test",
        "body": "user_3 notification received.",
        "url": "/"
    }
    
    success_count = 0
    for sub in subscriptions:
        subscription_data = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth
            }
        }
        
        try:
            webpush(
                subscription_info=subscription_data,
                data=json.dumps(message_payload),
                vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
                vapid_claims={"sub": settings.WEBPUSH_SETTINGS["VAPID_ADMIN_EMAIL"]}
            )
            print("Push sent successfully to user_1!")
            success_count += 1
        except WebPushException as ex:
            print(f"Failed: {ex}")
            if ex.response and ex.response.status_code in [404, 410]:
                sub.delete()
                
    return success_count
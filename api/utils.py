import json
from pywebpush import webpush, WebPushException
from django.conf import settings
from .models import PushSubscription

def send_test_notification():
    subscriptions = PushSubscription.objects.filter(user_id_str='user_1')
    
    message_payload = {
        "title": "push testing",
        "body": "user_3 notification testing",
        "url": "https://gogas1.iotronsys.com/alerts-dashboard?alertDate=2026-11-21&alertStationsId=%5B%5D&alertTypesId=%5B2%2C3%2C4%2C6%2C7%2C8%2C9%2C11%2C12%2C13%2C14%2C15%2C16%2C17%2C18%2C19%2C20%2C21%5D"
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
            print("Push sent successfully to user3")
            success_count += 1
        except WebPushException as ex:
            print(f"Failed: {ex}")
            if ex.response and ex.response.status_code in [404, 410]:
                sub.delete()
                
    return success_count
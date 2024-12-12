import requests
from django.conf import settings
from django.core.mail import send_mail

def send_email_notification(subject, message, sender, receiver ):
    
    from_email = sender
    recipient_list = (receiver,)
    return send_mail(subject, message, from_email, recipient_list,fail_silently=False)

# def send_email_notification(email, password, subject, message):
    
#     url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
#     auth = ("api", settings.MAILGUN_API_KEY)
#     data = {
#         "from": f"noreply@example.com",
#         "to": email,
#         "subject": subject,
#         "text": message
#     }
    
#     response = requests.post(url, auth=auth, data=data)
    
#     return bool(response.ok)
    
    
def send_sms_otp(mobile, otp):
    
    mobile = '+90' + mobile
    url = f"https://2factor.in/API/V1/{settings.SMS_API_KEY}/SMS/{mobile}/{otp}/Doğrulama kodunuz"
    payload = ''
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    response = requests.get(url, data=payload, headers=headers)
    
    return bool(response.ok)
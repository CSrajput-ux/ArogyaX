"""
ArogyaX Healthcare Platform — Email Notification Service
"""

from flask_mail import Mail, Message

mail_client = None

def init_mail(app):
    global mail_client
    mail_client = Mail(app)

def send_mail_safe(subject, recipient, body):
    """Deliver email notification gracefully without throwing unhandled exceptions."""
    if not mail_client or not recipient:
        return
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail_client.send(msg)
    except Exception as e:
        print(f"Mail delivery notice (non-fatal): {e}")

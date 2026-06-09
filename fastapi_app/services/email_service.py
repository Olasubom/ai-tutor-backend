"""Gmail / SMTP email delivery for auth and notifications."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


def is_smtp_configured() -> bool:
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    return bool(user and password)


def _smtp_settings() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_name": os.getenv("SMTP_FROM_NAME", "AITutor").strip(),
        "from_email": (os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER", "")).strip(),
    }


def send_email(*, to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
    """Send an email via SMTP. Returns True on success, False if SMTP is not configured."""
    cfg = _smtp_settings()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("smtp_not_configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f'{cfg["from_name"]} <{cfg["from_email"]}>'
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        logger.info("email_sent", extra={"to": to_email, "subject": subject})
        return True
    except Exception:
        logger.exception("email_send_failed", extra={"to": to_email})
        raise


def send_password_reset_email(*, to_email: str, code: str, name: Optional[str] = None) -> bool:
    greeting = f"Hi {name}," if name else "Hi,"
    subject = "Your AITutor password reset code"
    text_body = (
        f"{greeting}\n\n"
        f"Your verification code is: {code}\n\n"
        "This code expires in 10 minutes. If you did not request a password reset, "
        "you can ignore this email.\n\n"
        "— AITutor"
    )
    html_body = f"""
    <div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;color:#1f2937">
      <p>{greeting}</p>
      <p>Use this verification code to reset your AITutor password:</p>
      <p style="font-size:28px;font-weight:700;letter-spacing:6px;color:#2563eb">{code}</p>
      <p style="font-size:14px;color:#6b7280">This code expires in <strong>10 minutes</strong>.</p>
      <p style="font-size:13px;color:#9ca3af">If you did not request this, you can safely ignore this email.</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0" />
      <p style="font-size:12px;color:#9ca3af">AITutor — Learning Intelligence</p>
    </div>
    """
    return send_email(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body)

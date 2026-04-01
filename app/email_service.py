"""
Email service configuration.
If SMTP credentials are missing, emails are logged to the console for local testing.
"""

import os
from pathlib import Path


def _load_local_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_local_env()


def _load_django_fallback_env():
    settings_path = Path(__file__).resolve().parent.parent / "django_admin" / "shopkart_admin" / "settings.py"
    if not settings_path.exists():
        return

    namespace = {"__file__": str(settings_path)}
    try:
        exec(settings_path.read_text(encoding="utf-8"), namespace)
    except Exception:
        return

    fallback_map = {
        "SMTP_HOST": namespace.get("SMTP_HOST", "smtp.gmail.com"),
        "SMTP_PORT": str(namespace.get("SMTP_PORT", 587)),
        "SMTP_USER": namespace.get("SMTP_USER", ""),
        "SMTP_PASSWORD": namespace.get("SMTP_PASSWORD", ""),
        "FROM_EMAIL": namespace.get("FROM_EMAIL", ""),
        "EMAIL_ENABLED": str(namespace.get("EMAIL_ENABLED", False)).lower(),
    }

    for key, value in fallback_map.items():
        if value:
            os.environ.setdefault(key, value)


_load_django_fallback_env()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", f"ShopKart <{SMTP_USER}>") if SMTP_USER else "ShopKart <no-reply@shopkart.local>"
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"


def _smtp_ready() -> bool:
    return EMAIL_ENABLED and bool(SMTP_USER and SMTP_PASSWORD and SMTP_HOST and SMTP_PORT)


async def send_email(to: str, subject: str, html_body: str):
    if not _smtp_ready():
        print(f"\n[EMAIL DISABLED] SMTP not configured for real delivery.")
        print(f"[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n")
        return

    try:
        import aiosmtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"[EMAIL SENT] {to} <- {subject}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


async def send_welcome_email(to: str, name: str):
    await send_email(to, "Welcome to ShopKart!", f"<p>Welcome <b>{name}</b>! Happy Shopping!</p>")


async def send_signup_otp_email(to: str, name: str, otp: str):
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#2874f0">Verify Your Email</h2>
      <p>Hi <b>{name or 'there'}</b>, use this OTP to complete your ShopKart signup:</p>
      <div style="font-size:32px;font-weight:700;letter-spacing:6px;margin:20px 0;color:#111">{otp}</div>
      <p style="color:#666;font-size:13px">OTP expires in 10 minutes. If you did not request this, you can ignore this email.</p>
    </div>"""
    await send_email(to, "Your ShopKart Signup OTP", html)


async def send_password_reset_email(to: str, name: str, token: str):
    url = f"{SITE_URL}/reset-password?token={token}"
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#2874f0">Reset Your Password</h2>
      <p>Hi <b>{name}</b>, click below to reset your password:</p>
      <a href="{url}" style="background:#2874f0;color:#fff;padding:12px 28px;border-radius:4px;
         text-decoration:none;display:inline-block;margin:16px 0;font-weight:600">Reset Password</a>
      <p style="color:#888;font-size:13px">Link expires in 1 hour. Ignore if you didn't request this.</p>
    </div>"""
    await send_email(to, "Reset Your ShopKart Password", html)


async def send_order_confirmation_email(to: str, name: str, order_id: str, items: list, total: float):
    rows = "".join(f"<tr><td>{i.get('product_id','')}</td><td>x{i.get('quantity',1)}</td></tr>" for i in items)
    html = f"""<div style="font-family:sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#388e3c">Order Confirmed! #{order_id}</h2>
      <p>Hi <b>{name}</b>, your order has been placed successfully.</p>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#f5f5f5"><th style="padding:8px">Product</th><th>Qty</th></tr>{rows}
      </table>
      <p style="font-size:16px;font-weight:700;margin-top:16px">Total: Rs.{total:,.0f}</p>
      <p style="color:#555;font-size:13px">Expected delivery: 3-5 business days</p>
    </div>"""
    await send_email(to, f"Order #{order_id} Confirmed - ShopKart", html)

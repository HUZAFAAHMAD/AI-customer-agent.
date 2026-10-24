# email_alert.py
import json
import os
import smtplib
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")


def _send_via_https_api(api_key: str, sender: str, receiver: str, subject: str, content: str) -> str:
    """Sends email over HTTPS (Port 443) using Resend's REST API.
    Bypasses all cloud container SMTP port blocks."""
    url = "https://api.resend.com/emails"
    from_addr = sender if ("@" in (sender or "") and not (sender or "").endswith("@gmail.com")) else "SupportAI <onboarding@resend.dev>"
    payload = json.dumps({
        "from": from_addr,
        "to": [receiver],
        "subject": subject,
        "text": content,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "SupportAI/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            return f"Email sent successfully via HTTPS API to {receiver} (ID: {result.get('id', 'ok')})"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        print(f"[email-alert] Resend HTTP Error {e.code}: {err_msg}")
        return f"Email failed via Resend (HTTP {e.code}): {err_msg}"


def _send_via_smtp(sender: str, password: str, receiver: str, host: str, port: int, msg: EmailMessage) -> str:
    """Fallback standard SMTP for local development."""
    password = password.strip().replace(" ", "")
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            server.login(sender, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
    return f"Email sent successfully via SMTP to {receiver}"


def send_severity_alert_email(
    query: str, severity: str, session_id: str = "unknown"
) -> str:
    """Send an email alert to the support team about an urgent customer issue."""
    resend_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 587))

    if not receiver:
        return "Email skipped: EMAIL_RECEIVER not configured"

    subject = f"[{severity.upper()} SEVERITY] Customer support issue"
    content = (
        f"A high-severity customer issue was detected.\n\n"
        f"Severity:   {severity}\n"
        f"Session ID: {session_id}\n"
        f"Time (UTC): {datetime.utcnow():%Y-%m-%d %H:%M:%S}\n\n"
        f"Customer message:\n{query}\n"
    )

    # 1. Primary: Use HTTPS REST API on Railway (Port 443 — NEVER blocked)
    if resend_key:
        res = _send_via_https_api(resend_key, sender or "SupportAI", receiver, subject, content)
        if "successfully" in res:
            return res
        print(f"[email-alert] HTTPS attempt did not succeed: {res}")
        if not (sender and password):
            return res
        # If both are configured, try SMTP fallback
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = receiver
        msg.set_content(content)
        try:
            return _send_via_smtp(sender, password, receiver, host, port, msg)
        except Exception as smtp_err:
            return f"{res}. SMTP fallback also failed: {smtp_err}"

    # 2. Fallback: Use standard SMTP (for local development or unblocked networks)
    if not (sender and password):
        return "Email skipped: No RESEND_API_KEY and missing SMTP credentials"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(content)

    try:
        return _send_via_smtp(sender, password, receiver, host, port, msg)
    except Exception as e:
        print(f"[email-alert] Failed to send email via {host}:{port}: {e}")
        return f"Email failed: {e}"
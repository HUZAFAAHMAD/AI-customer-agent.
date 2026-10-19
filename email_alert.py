# email_alert.py
"""
CHANGED: this file used to own its own `threading.Thread(...).start()`
fire-and-forget wrapper (`trigger_high_severity_email`). That's moved out
to alert_queue.py, which replaces "spawn a brand new thread per request"
with "push a job onto a durable queue, drained by one persistent worker".
This file now does exactly one thing: send the email when asked to.

NOTE: your pipeline imported this as `from email_alert import ...`, but the
file you pasted was headed `#emailalert.py` (no underscore). Make sure the
actual filename on disk is `email_alert.py` — otherwise that import raises
ModuleNotFoundError.
"""
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")


def send_severity_alert_email(
    query: str, severity: str, session_id: str = "unknown"
) -> str:
    """Send an email alert to the support team about an urgent customer issue.
    Use only when the classified severity is 'high'. Blocking/synchronous —
    the caller (alert_queue.py's worker) is responsible for running this
    off the request path."""
    if not (EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECEIVER):
        return "Email skipped: credentials missing in .env"

    msg = EmailMessage()
    msg["Subject"] = f"[{severity.upper()} SEVERITY] Customer support issue"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(
        f"A high-severity customer issue was detected.\n\n"
        f"Severity:   {severity}\n"
        f"Session ID: {session_id}\n"
        f"Time (UTC): {datetime.utcnow():%Y-%m-%d %H:%M:%S}\n\n"
        f"Customer message:\n{query}\n"
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return "Email sent"
    except Exception as e:
        return f"Email failed: {e}"

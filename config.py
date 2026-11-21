import os
from dotenv import load_dotenv

load_dotenv()  # read .env file and load variables from it

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Redis configuration (supports REDIS_URL, REDIS_PRIVATE_URL, or Railway REDISHOST/REDISPASSWORD)
import urllib.parse


def get_redis_url() -> str:
    url = os.getenv("REDIS_URL") or os.getenv("REDIS_PRIVATE_URL") or os.getenv("REDIS_PUBLIC_URL")
    if url and url.strip():
        return url.strip()

    host = os.getenv("REDISHOST") or os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDISPORT") or os.getenv("REDIS_PORT", "6379")
    user = os.getenv("REDISUSER") or os.getenv("REDIS_USER", "default")
    password = os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD", "")

    if password:
        encoded_pass = urllib.parse.quote_plus(password.strip())
        return f"redis://{user}:{encoded_pass}@{host}:{port}/0"
    return f"redis://{host}:{port}/0"


REDIS_URL = get_redis_url()
REDIS_HOST = os.getenv("REDISHOST") or os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT", 6379))

# SMTP configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# Pipeline Defaults
DEFAULT_RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.40"))
DEFAULT_RERANK_MIN_SCORE = float(os.getenv("RERANK_MIN_SCORE", "4.0"))
KB_VERSION = os.getenv("KB_VERSION", "v1.0")
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1.0")

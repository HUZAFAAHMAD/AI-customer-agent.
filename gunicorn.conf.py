import os

# Gunicorn configuration file for production (Railway / Docker)
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", 1))
threads = int(os.getenv("GUNICORN_THREADS", 6))
worker_class = "gthread"
timeout = 180
graceful_timeout = 30
keepalive = 65

# Use in-memory temporary directory for worker heartbeats to prevent
# false WORKER TIMEOUT kills caused by container disk I/O latency.
if os.path.exists("/dev/shm"):
    worker_tmp_dir = "/dev/shm"

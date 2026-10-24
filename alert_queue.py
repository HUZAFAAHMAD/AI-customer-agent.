# alert_queue.py
"""
REPLACES: `threading.Thread(target=trigger_high_severity_email, ...).start()`
fired fresh on every single high-severity request.

Why that was a real problem at any real traffic volume:
  - Unbounded thread creation: a burst of high-severity messages spawns a
    burst of OS threads with no cap, no backpressure, and no queueing.
  - If the process restarts (crash, deploy) while a thread is mid-send,
    that alert is just gone — nothing durable ever recorded that it was
    supposed to go out.
  - No retry path: if the SMTP call fails, the exception is swallowed
    inside a daemon thread and nobody finds out.

This file replaces that with a small, durable job queue: `enqueue_alert()`
does a non-blocking Redis RPUSH and returns immediately (same "don't make
the customer wait" property as before), and exactly ONE persistent
background thread drains the queue with a blocking BLPOP (no busy-wait
polling loop). Because the queue lives in Redis, not in process memory,
a job survives a restart of the app process — it just sits in the list
until the worker is back up.

This reuses the same Redis instance you're already running for session
history (redis_memory / rag_pipeline.py), so it's not a new piece of
infrastructure — just a second use of the one you already have.

For heavier production needs (retry-with-backoff, dead-letter queue,
multiple worker processes, monitoring/dashboards), RQ or Celery build on
this exact same idea on top of Redis — this file is the minimal version
of that pattern.
"""
import json
import os
import threading
import time

import redis

from email_alert import send_severity_alert_email
from config import REDIS_URL

ALERT_QUEUE_KEY = "severity_alert_queue"

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_timeout=10,
)

_worker_thread = None
_worker_lock = threading.Lock()


def enqueue_alert(query: str, severity: str, session_id: str) -> None:
    """Non-blocking: push the alert job onto the Redis queue and return
    immediately. Call this from the request path exactly where the old
    threading.Thread(...).start() call used to sit."""
    if severity != "high":
        return
    # convert this python dictionery into string
    payload = json.dumps(
        {"query": query, "severity": severity, "session_id": session_id}
    )
    try:
        redis_client.rpush(ALERT_QUEUE_KEY, payload)
    except Exception as exc:
        print(f"[alert-queue] failed to enqueue alert: {exc}")


def _worker_loop() -> None:
    while True:
        try:
            # BLPOP blocks until a job shows up - no busy-wait polling, and the
            # queue (and any jobs waiting in it) survives an app restart because
            # it lives in Redis, not in this thread's memory.
            item = redis_client.blpop(ALERT_QUEUE_KEY, timeout=5)
            if item is None:
                continue
            _, raw_payload = item
            # convert getting string into back pyton dictionery
            job = json.loads(raw_payload)
            result = send_severity_alert_email(
                query=job["query"],
                severity=job["severity"],
                session_id=job["session_id"],
            )
            print(f"[alert-worker] {result}")
        except (redis.ConnectionError, redis.TimeoutError, redis.AuthenticationError) as conn_err:
            # Reconnect resilience: network blips or Redis restarts should never kill the worker
            print(
                f"[alert-worker] Redis connection or auth error, retrying in 5s: {conn_err}"
            )
            time.sleep(5)
        except Exception as exc:
            # a bad job should never kill the worker loop - log and move on
            print(f"[alert-worker] failed to process alert job: {exc}")


def start_alert_worker() -> None:
    """Call once at application startup (rag_pipeline.py does this at
    import time). Spawns exactly ONE background worker thread that drains
    the Redis alert queue for the lifetime of the process - replaces the
    old pattern of spawning a brand-new thread per high-severity request.
    Safe to call more than once; it's a no-op if the worker is already
    running."""
    global _worker_thread
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_worker_loop, name="alert-worker", daemon=True
            )
            _worker_thread.start()


# Reddit queue only accept string thats why first it covert dictionery into string then string into dictionery

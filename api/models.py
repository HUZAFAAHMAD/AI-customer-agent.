from django.db import models

class AIRequest(models.Model):
    session_id = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    input_text = models.TextField()
    output_text = models.TextField()
    model_name = models.CharField(max_length=100, default="gemini-3.1-flash-lite")
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    latency_ms = models.FloatField(default=0.0)
    cache_hit = models.BooleanField(default=False)
    severity = models.CharField(max_length=20, null=True, blank=True)
    complexity = models.CharField(max_length=20, null=True, blank=True)
    source = models.CharField(max_length=50, default="rag") # rag, cache, fallback
    retrieval_count = models.IntegerField(default=0)
    rerank_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, default="success") # success, error, fallback
    error_message = models.TextField(null=True, blank=True)
    
    # Step latency breakdown in milliseconds (for Request Details Trace in Admin)
    embedding_latency_ms = models.FloatField(default=0.0)
    cache_latency_ms = models.FloatField(default=0.0)
    analysis_latency_ms = models.FloatField(default=0.0)
    retrieval_latency_ms = models.FloatField(default=0.0)
    rerank_latency_ms = models.FloatField(default=0.0)
    generation_latency_ms = models.FloatField(default=0.0)
    sources = models.TextField(default="[]")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at.strftime('%H:%M:%S')}] {self.input_text[:30]}"


class AIModelConfig(models.Model):
    name = models.CharField(max_length=100, default="Active Configuration")
    primary_model = models.CharField(max_length=100, default="gemini-3.1-flash-lite")
    backup_model = models.CharField(max_length=100, default="gemini-3.1-flash-lite")
    embedding_model = models.CharField(max_length=100, default="sentence-transformers/all-MiniLM-L6-v2")
    temperature = models.FloatField(default=0.2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.primary_model}"


class EmailAlertLog(models.Model):
    session_id = models.CharField(max_length=100)
    query = models.TextField()
    severity = models.CharField(max_length=20, default="high")
    status = models.CharField(max_length=30, default="sent")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alert ({self.severity}) - {self.query[:30]}"

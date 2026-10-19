from rest_framework import serializers
from .models import AIRequest, AIModelConfig, EmailAlertLog
from django.utils import timezone
import json

class AIRequestSerializer(serializers.ModelSerializer):
    formatted_time = serializers.SerializerMethodField()
    step_timings = serializers.SerializerMethodField()
    sources_list = serializers.SerializerMethodField()

    class Meta:
        model = AIRequest
        fields = [
            "id",
            "session_id",
            "created_at",
            "formatted_time",
            "input_text",
            "output_text",
            "model_name",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "latency_ms",
            "cache_hit",
            "severity",
            "complexity",
            "source",
            "retrieval_count",
            "rerank_score",
            "status",
            "error_message",
            "embedding_latency_ms",
            "cache_latency_ms",
            "analysis_latency_ms",
            "retrieval_latency_ms",
            "rerank_latency_ms",
            "generation_latency_ms",
            "step_timings",
            "sources_list",
        ]

    def get_formatted_time(self, obj):
        if not obj.created_at:
            return ""
        return timezone.localtime(obj.created_at).strftime("%I:%M %p")

    def get_step_timings(self, obj):
        return {
            "embedding": getattr(obj, "embedding_latency_ms", 0.0),
            "cache": obj.cache_latency_ms,
            "analysis": obj.analysis_latency_ms,
            "retrieval": obj.retrieval_latency_ms,
            "reranking": obj.rerank_latency_ms,
            "generation": obj.generation_latency_ms,
            "total": obj.latency_ms,
        }

    def get_sources_list(self, obj):
        try:
            return json.loads(obj.sources)
        except Exception:
            return []


class AIModelConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelConfig
        fields = [
            "id",
            "name",
            "primary_model",
            "backup_model",
            "embedding_model",
            "temperature",
            "is_active",
            "created_at",
        ]


class EmailAlertLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAlertLog
        fields = [
            "id",
            "session_id",
            "query",
            "severity",
            "status",
            "created_at",
        ]

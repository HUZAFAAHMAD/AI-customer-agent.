from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Avg, Sum, Count
from datetime import datetime, timedelta
import redis
import os
import json

from django.http import StreamingHttpResponse
from .models import AIRequest, AIModelConfig, EmailAlertLog
from .serializers import AIRequestSerializer, AIModelConfigSerializer, EmailAlertLogSerializer
from .pipeline_service import run_pipeline_with_metrics, stream_pipeline_with_metrics
import main


# ──────────────────────────────────────────────────────────
# 1. CUSTOMER CHAT ENDPOINTS (Public / AllowAny)
# ──────────────────────────────────────────────────────────

class ChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        query = request.data.get("query", "").strip()
        session_id = request.data.get("session_id", "").strip()

        if not query:
            return Response({"error": "Query cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        if not session_id:
            session_id = f"session_{int(datetime.utcnow().timestamp())}"

        try:
            result = run_pipeline_with_metrics(query, session_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as err:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": str(err), "answer": f"Error processing query: {str(err)}", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatStreamView(APIView):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams tokens in real-time as they are produced by the LLM for ~500ms time-to-first-token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        query = request.data.get("query", "").strip()
        session_id = request.data.get("session_id", "").strip()

        if not query:
            return Response({"error": "Query cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        if not session_id:
            session_id = f"session_{int(datetime.utcnow().timestamp())}"

        response = StreamingHttpResponse(
            stream_pipeline_with_metrics(query, session_id),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ChatHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id", "").strip()
        if not session_id:
            return Response([], status=status.HTTP_200_OK)

        history = main.get_history(session_id)
        return Response(history, status=status.HTTP_200_OK)


class ChatClearView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id", "").strip()
        if session_id:
            try:
                main.redis_client.delete(f"chat_history:{session_id}")
            except Exception:
                pass
        return Response({"status": "cleared"}, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────
# 2. ADMIN MONITORING ENDPOINTS
# ──────────────────────────────────────────────────────────

class AdminStatsView(APIView):
    # Allows both authenticated admin and demo access
    permission_classes = [AllowAny]

    def get(self, request):
        total_requests = AIRequest.objects.count()
        cache_hits = AIRequest.objects.filter(cache_hit=True).count()
        cache_hit_rate = round((cache_hits / total_requests * 100), 1) if total_requests > 0 else 0.0

        avg_lat_obj = AIRequest.objects.aggregate(Avg("latency_ms"))["latency_ms__avg"]
        avg_latency = round(avg_lat_obj / 1000, 2) if avg_lat_obj else 0.0

        total_tok_obj = AIRequest.objects.aggregate(Sum("total_tokens"))["total_tokens__sum"]
        total_tokens = total_tok_obj if total_tok_obj else 0

        # Estimate cost: ~$0.15 per 1M tokens average for Flash models
        estimated_cost = round((total_tokens / 1_000_000) * 0.15, 3)

        emails_sent = EmailAlertLog.objects.count()
        high_severity_count = AIRequest.objects.filter(severity="high").count()

        # Build 7-day request trend for the chart
        daily_trends = []
        now = datetime.utcnow()
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            day_reqs = AIRequest.objects.filter(created_at__date=day).count()
            day_cache = AIRequest.objects.filter(created_at__date=day, cache_hit=True).count()
            daily_trends.append({
                "date": day.strftime("%b %d"),
                "requests": day_reqs,
                "cache_hits": day_cache,
            })

        return Response({
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "avg_latency": avg_latency,
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "emails_sent": emails_sent,
            "high_severity_count": high_severity_count,
            "daily_trends": daily_trends,
        }, status=status.HTTP_200_OK)


class AIRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Standard ModelViewSet (Phase 3 of your notes)
    Provides list (/api/admin/requests/) and retrieve (/api/admin/requests/<id>/)
    """
    queryset = AIRequest.objects.all().order_by("-created_at")
    serializer_class = AIRequestSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search", None)
        if search:
            qs = qs.filter(input_text__icontains=search)
        return qs[:100]


class AIModelConfigViewSet(viewsets.ModelViewSet):
    """
    Manage primary, backup, and embedding model configurations.
    """
    queryset = AIModelConfig.objects.all()
    serializer_class = AIModelConfigSerializer
    permission_classes = [AllowAny]


class SystemStatusView(APIView):
    """
    Reports live health of API, Database, Redis, and Email services.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. API is online (we are inside the view)
        api_status = "Online"

        # 2. Database check
        try:
            AIRequest.objects.exists()
            db_status = "Online"
        except Exception:
            db_status = "Offline"

        # 3. Redis check
        try:
            main.redis_client.ping()
            redis_status = "Online"
        except Exception:
            redis_status = "Offline"

        # 4. Email check (credentials presence)
        email_status = "Online" if (os.getenv("EMAIL_SENDER") and os.getenv("EMAIL_PASSWORD")) else "Configured"

        return Response({
            "api": api_status,
            "database": db_status,
            "redis": redis_status,
            "email": email_status,
        }, status=status.HTTP_200_OK)


class SystemResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        import shutil
        import sqlite3
        import redis
        
        results = []

        # 1. Django Models
        try:
            AIRequest.objects.all().delete()
            EmailAlertLog.objects.all().delete()
            results.append("Cleared Django DB logs")
        except Exception as e:
            results.append(f"Django DB error: {e}")

        # 2. Redis
        try:
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            keys = r.keys('chat_history:*')
            if keys:
                r.delete(*keys)
            exact_keys = r.keys('exact_cache:*')
            if exact_keys:
                r.delete(*exact_keys)
            r.delete('severity_alert_queue')
            results.append(f"Cleared Redis ({len(keys)} history keys, {len(exact_keys)} exact_cache keys + queue)")
        except Exception as e:
            results.append(f"Redis error: {e}")

        # 3. FTS5
        try:
            if os.path.exists('./fts5_index.db'):
                con = sqlite3.connect('./fts5_index.db')
                con.execute('DELETE FROM kb_fts')
                con.commit()
                con.close()
                results.append("Cleared FTS5 index")
        except Exception as e:
            results.append(f"FTS5 error: {e}")

        # 4. ChromaDB (via API since server is running)
        try:
            import chromadb
            # Clear knowledge base
            try:
                client = chromadb.PersistentClient(path='./chroma_kb')
                cols = client.list_collections()
                for c in cols:
                    client.delete_collection(c.name)
                client.get_or_create_collection('novatek_kb_minilm', metadata={"hnsw:space": "cosine"})
                results.append("Cleared Chroma knowledge base")
            except Exception as e:
                pass
            
            # Clear cache
            try:
                client2 = chromadb.PersistentClient(path='./chroma_cache')
                cols2 = client2.list_collections()
                for c in cols2:
                    client2.delete_collection(c.name)
                client2.get_or_create_collection('semantic_cache_minilm', metadata={"hnsw:space": "cosine"})
                results.append("Cleared Chroma semantic cache")
            except Exception as e:
                pass
                
            # Rebind in-memory handles to new collections
            main.cache_vectorstore = None
            main.kb_vectorstore = None
            main.get_cache_vectorstore()
            main.get_kb_vectorstore()
            add_documents.kb_vectorstore = None
            add_documents.get_kb_vectorstore()
        except Exception as e:
            results.append(f"ChromaDB error: {e}")
            
        return Response({"status": "success", "results": results}, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────
# 3. DOCUMENT MANAGEMENT (ChromaDB + SQLite FTS5)
# ──────────────────────────────────────────────────────────
import add_documents
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class DocumentManagementView(APIView):
    """
    Directly leverages add_documents.py process 100% to add,
    list, and delete documents from both ChromaDB and FTS5 index.
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        try:
            docs = add_documents.list_documents()
            stats = add_documents.show_stats()
            return Response({
                "documents": docs,
                "stats": stats
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "documents": [],
                "stats": {"chroma_chunks": 0, "fts_chunks": 0},
                "error": str(e)
            }, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            # 1. Uploaded PDF file
            if "file" in request.FILES:
                uploaded_file = request.FILES["file"]
                os.makedirs("./uploaded_docs", exist_ok=True)
                saved_path = os.path.join("./uploaded_docs", uploaded_file.name)
                with open(saved_path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                
                # Use user's exact add_documents pipeline 100%
                chunks_added = add_documents.add_pdf(saved_path)
                return Response({
                    "status": "success",
                    "source": uploaded_file.name,
                    "chunks_added": chunks_added,
                    "message": f"Successfully indexed {uploaded_file.name} ({chunks_added} chunks) into ChromaDB and FTS5."
                }, status=status.HTTP_201_CREATED)

            # 2. Re-index techmart_support_guide.pdf (quick 1-click convenience)
            elif request.data.get("reindex_default"):
                pdf_path = "./techmart_support_guide.pdf"
                if os.path.exists(pdf_path):
                    chunks_added = add_documents.add_pdf(pdf_path)
                    return Response({
                        "status": "success",
                        "source": "techmart_support_guide.pdf",
                        "chunks_added": chunks_added,
                        "message": f"Successfully re-indexed techmart_support_guide.pdf ({chunks_added} chunks)."
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": "techmart_support_guide.pdf not found"}, status=status.HTTP_404_NOT_FOUND)

            # 3. Add plain text policy / FAQ directly
            elif request.data.get("text"):
                text = request.data["text"].strip()
                source_name = request.data.get("source_name", "manual_policy").strip()
                chunks_added = add_documents.add_text(text, source_name=source_name)
                return Response({
                    "status": "success",
                    "source": source_name,
                    "chunks_added": chunks_added,
                    "message": f"Successfully added {chunks_added} chunks for {source_name}."
                }, status=status.HTTP_201_CREATED)

            return Response({"error": "No file or text provided."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to index document: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            source = request.query_params.get("source") or request.data.get("source")
            if not source:
                return Response({"error": "source name required."}, status=status.HTTP_400_BAD_REQUEST)
            
            add_documents.delete_document(source)
            return Response({
                "status": "deleted",
                "source": source,
                "message": f"Successfully deleted {source} from ChromaDB and FTS5."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to delete document: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


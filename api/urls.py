from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatView,
    ChatStreamView,
    ChatHistoryView,
    ChatClearView,
    AdminStatsView,
    AIRequestViewSet,
    AIModelConfigViewSet,
    SystemStatusView,
    SystemResetView,
    CacheClearView,
    DocumentManagementView,
)

router = DefaultRouter()
router.register("requests", AIRequestViewSet, basename="admin-requests")
router.register("models", AIModelConfigViewSet, basename="admin-models")

urlpatterns = [
    # Customer Chat
    path("chat/", ChatView.as_view(), name="chat"),
    path("chat/stream/", ChatStreamView.as_view(), name="chat-stream"),
    path("chat/history/", ChatHistoryView.as_view(), name="chat-history"),
    path("chat/clear/", ChatClearView.as_view(), name="chat-clear"),

    # Admin Monitoring & Telemetry
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("system/", SystemStatusView.as_view(), name="system-status"),
    path("system/reset/", SystemResetView.as_view(), name="system-reset"),
    path("cache/clear/", CacheClearView.as_view(), name="cache-clear"),
    path("documents/", DocumentManagementView.as_view(), name="documents"),

    # ViewSets (router generates /requests/, /requests/<id>/, /models/, etc.)
    path("", include(router.urls)),
]

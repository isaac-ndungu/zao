from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AuditLogViewSet,
    FarmerPaymentHistoryView,
    LatestStatementPDFView,
    SeasonReportPDFView,
    StatementPDFView,
)

router = SimpleRouter()
router.register('audit', AuditLogViewSet)

urlpatterns = [
    path('statement/', StatementPDFView.as_view(), name='statement-pdf'),
    path('statement/latest/', LatestStatementPDFView.as_view(), name='statement-latest'),
    path('statement/history/', FarmerPaymentHistoryView.as_view(), name='statement-history'),
    path('report/', SeasonReportPDFView.as_view(), name='season-report'),
] + router.urls

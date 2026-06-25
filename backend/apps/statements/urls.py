from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AnnualReportView,
    AuditLogViewSet,
    ExternalAuditLogViewSet,
    FarmerPaymentHistoryView,
    KRAReportPDFView,
    LatestStatementPDFView,
    SeasonReportPDFView,
    StatementPDFView,
)

router = SimpleRouter()
router.register('audit', AuditLogViewSet)
router.register('external-audit', ExternalAuditLogViewSet)

urlpatterns = [
    path('annual-report/', AnnualReportView.as_view(), name='annual-report'),
    path('statement/', StatementPDFView.as_view(), name='statement-pdf'),
    path('statement/latest/', LatestStatementPDFView.as_view(), name='statement-latest'),
    path('statement/history/', FarmerPaymentHistoryView.as_view(), name='statement-history'),
    path('report/', SeasonReportPDFView.as_view(), name='season-report'),
    path('kra-report/', KRAReportPDFView.as_view(), name='kra-report'),
] + router.urls


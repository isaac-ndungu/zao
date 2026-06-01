from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AuditLogViewSet,
    FarmerPaymentHistoryView,
    KRAReportPDFView,
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
    path('kra-report/', KRAReportPDFView.as_view(), name='kra-report'),
] + router.urls

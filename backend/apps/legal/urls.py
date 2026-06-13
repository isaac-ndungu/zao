from django.urls import path

from . import views

urlpatterns = [
    path('legal/pending-acceptance/', views.PendingAcceptanceView.as_view(), name='legal-pending-acceptance'),
    path('legal/<slug:slug>/accept/', views.LegalAcceptanceView.as_view(), name='legal-accept'),
    path('legal/<slug:slug>/versions/', views.LegalDocumentVersionListView.as_view(), name='legal-versions'),
    path('legal/<slug:slug>/<int:version>/', views.LegalDocumentVersionDetailView.as_view(), name='legal-version-detail'),
    path('legal/<slug:slug>/', views.LegalDocumentDetailView.as_view(), name='legal-detail'),
]

from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.idempotency import idempotent
from apps.base.utils import log_audit

from .models import LegalDocument, LegalAcceptance
from .serializers import (
    LegalDocumentDetailSerializer,
    LegalDocumentListSerializer,
    PendingLegalDocumentSerializer,
)
from .throttles import LegalDocumentAnonThrottle


class LegalDocumentDetailView(APIView):
    permission_classes = []
    throttle_classes = [LegalDocumentAnonThrottle]

    def get(self, request, slug):
        doc = LegalDocument.objects.filter(
            slug=slug,
            is_active=True,
            published_at__lte=timezone.now(),
        ).order_by('-version').first()
        if not doc:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = LegalDocumentDetailSerializer(doc)
        return Response(serializer.data)


class LegalDocumentVersionListView(APIView):
    permission_classes = []
    throttle_classes = [LegalDocumentAnonThrottle]

    def get(self, request, slug):
        docs = LegalDocument.objects.filter(
            slug=slug,
            is_active=True,
            published_at__lte=timezone.now(),
        ).order_by('-version')
        if not docs.exists():
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = LegalDocumentListSerializer(docs, many=True)
        return Response(serializer.data)


class LegalDocumentVersionDetailView(APIView):
    permission_classes = []
    throttle_classes = [LegalDocumentAnonThrottle]

    def get(self, request, slug, version):
        doc = LegalDocument.objects.filter(
            slug=slug,
            version=version,
            is_active=True,
            published_at__lte=timezone.now(),
        ).first()
        if not doc:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = LegalDocumentDetailSerializer(doc)
        return Response(serializer.data)


class LegalAcceptanceView(APIView):
    permission_classes = [IsAuthenticated]

    @idempotent()
    def post(self, request, slug):
        doc = LegalDocument.objects.filter(
            slug=slug,
            is_active=True,
            published_at__lte=timezone.now(),
        ).order_by('-version').first()
        if not doc:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not doc.requires_acceptance:
            return Response(
                {'detail': 'This document does not require acceptance.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, created = LegalAcceptance.objects.get_or_create(
            user=request.user,
            document=doc,
            version=doc.version,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            },
        )
        if created:
            log_audit(
                actor=request.user,
                resource_type='legal_document',
                resource_id=doc.pk,
                action='ACCEPT',
                new_value={'slug': doc.slug, 'version': doc.version},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return Response({'detail': 'Accepted.'}, status=status.HTTP_200_OK)


class PendingAcceptanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        has_accepted = Exists(
            LegalAcceptance.objects.filter(
                user=request.user,
                document=OuterRef('pk'),
                version=OuterRef('version'),
            )
        )
        pending_docs = LegalDocument.objects.filter(
            is_active=True,
            requires_acceptance=True,
            published_at__lte=timezone.now(),
        ).annotate(has_accepted=has_accepted).filter(
            has_accepted=False,
        ).order_by('-version')

        data = PendingLegalDocumentSerializer(pending_docs, many=True).data
        return Response({'pending_documents': data})

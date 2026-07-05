from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.idempotency import idempotent
from apps.base.models import AuditAction
from apps.base.utils import log_audit

from .models import LegalDocument, LegalAcceptance
from .serializers import (
    LegalDocumentDetailSerializer,
    LegalDocumentListSerializer,
    MyAcceptanceSerializer,
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
        # Optional version check: if the client asserts a version, it must
        # match the currently active version. A mismatch means the client
        # was looking at a stale page; tell them to reload. Returning 400
        # (not 409) signals "request is well-formed but semantically wrong"
        # rather than a retryable conflict.
        if 'version' in request.data:
            try:
                requested_version = int(request.data['version'])
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'Invalid version.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if requested_version != doc.version:
                return Response(
                    {
                        'detail': (
                            f"Version mismatch. You are accepting version "
                            f"{requested_version} but the current version is "
                            f"{doc.version}. Please reload the page."
                        ),
                    },
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
                action=AuditAction.ACCEPT,
                new_value={'slug': doc.slug, 'version': doc.version},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return Response({'detail': 'Accepted.'}, status=status.HTTP_200_OK)


class PendingAcceptanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Phase 2 simplification: because the partial UniqueConstraint
        # guarantees at most one active row per slug, matching on
        # ``document=OuterRef('pk')`` is sufficient. The previous
        # ``version=OuterRef('version')`` clause caused users to be re-prompted
        # for a v1 they had already implicitly accepted by accepting v2.
        has_accepted = Exists(
            LegalAcceptance.objects.filter(
                user=request.user,
                document=OuterRef('pk'),
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


class MyAcceptanceView(APIView):
    """Return the current user's acceptance state for a given legal document.

    Used by the public ``/legal/<slug>/`` page to render a "you previously
    accepted v1; please review and accept the new terms" banner. The page
    is unauthenticated, so the front-end silently ignores 401 (anonymous
    visitor) and shows the document without the banner.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        doc = (LegalDocument.objects
               .filter(slug=slug, is_active=True,
                       published_at__lte=timezone.now())
               .order_by('-version').first())
        if not doc:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        acceptance = (LegalAcceptance.objects
                      .filter(user=request.user, document__slug=slug)
                      .order_by('-version')
                      .first())
        payload = {
            'accepted': acceptance is not None,
            'accepted_version': acceptance.version if acceptance else None,
            'accepted_at': acceptance.accepted_at if acceptance else None,
            'current_version': doc.version,
        }
        return Response(MyAcceptanceSerializer(payload).data)

import csv

from django.db import transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base.models import AuditAction
from apps.base.permissions import IsAdminOrSuperUser
from apps.base.utils import log_audit

from .models import LegalAcceptance, LegalDocument
from .serializers import (
    LegalAcceptanceAdminSerializer,
    LegalDocumentAdminSerializer,
    LegalDocumentListSerializer,
)


class LegalDocumentAdminViewSet(viewsets.ModelViewSet):
    """Platform-admin CRUD for legal documents (privacy policy, ToS, etc.).

    `publish` creates a NEW version row (preserves version history) and
    marks it active. `published_at` is set by the publish action only;
    the serializer leaves it read-only so admins can't bypass versioning.
    """
    permission_classes = [IsAdminOrSuperUser]
    queryset = LegalDocument.objects.all().order_by('-published_at', '-version')
    serializer_class = LegalDocumentAdminSerializer
    filterset_fields = ['slug', 'is_active', 'requires_acceptance']
    search_fields = ['slug', 'title']
    lookup_field = 'id'

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='legal_document',
            resource_id=instance.id,
            action=AuditAction.CREATE,
            new_value=serializer.data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='legal_document',
            resource_id=instance.id,
            action=AuditAction.UPDATE,
            new_value=serializer.data,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='legal_document',
            resource_id=instance.id,
            action=AuditAction.DELETE,
            previous_value={'slug': instance.slug, 'version': instance.version},
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, id=None):
        doc = self.get_object()
        latest = (
            LegalDocument.objects.filter(slug=doc.slug)
            .order_by('-version')
            .first()
        )
        new_version = (latest.version + 1) if latest else 1
        new_doc = LegalDocument.objects.publish_new(
            slug=doc.slug,
            actor=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            title=doc.title,
            content=doc.content,
            version=new_version,
            requires_acceptance=doc.requires_acceptance,
            published_at=timezone.now(),
        )
        return Response(LegalDocumentAdminSerializer(new_doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, id=None):
        """Emergency takedown: mark a single version inactive.

        Guards:
        * The doc must currently be ``is_active=True`` (deactivating an
          already-inactive row is a no-op error).
        * Requires ``?confirm=true`` query param so a misclick doesn't
          silently leave the platform without an active privacy policy /
          ToS. Without confirm, returns 400 with a clear message.
        """
        if request.query_params.get('confirm') != 'true':
            return Response(
                {
                    'detail': (
                        "Deactivation requires ?confirm=true. NOTE: this will "
                        "leave no active version of the document; users will "
                        "not be prompted to accept any version of this "
                        "document until a new version is published."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        doc = self.get_object()
        if not doc.is_active:
            return Response(
                {'detail': f"{doc.slug} v{doc.version} is already inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            doc.is_active = False
            doc.save(update_fields=['is_active', 'updated_at'])
            log_audit(
                actor=request.user,
                resource_type='LegalDocument',
                resource_id=doc.pk,
                action=AuditAction.DEACTIVATE,
                previous_value={
                    'slug': doc.slug, 'version': doc.version, 'is_active': True,
                },
                new_value={
                    'slug': doc.slug, 'version': doc.version, 'is_active': False,
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return Response({
            'detail': (
                f"Deactivated {doc.slug} v{doc.version}. There is now no "
                f"active version of '{doc.slug}'."
            ),
        })


class LegalAcceptanceLogView(APIView):
    """Compliance log of who accepted which document version when.

    Supports filters: ?slug=, ?user_id=, ?date_from=, ?date_to=,
    ?format=csv (streams a CSV download).
    """
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        qs = LegalAcceptance.objects.select_related('user', 'document').all()
        slug = request.query_params.get('slug')
        if slug:
            qs = qs.filter(document__slug=slug)
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(accepted_at__date__gte=date_from)
        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(accepted_at__date__lte=date_to)
        qs = qs.order_by('-accepted_at')[:500]

        if request.query_params.get('format') == 'csv':
            return self._csv(qs)
        data = LegalAcceptanceAdminSerializer(qs, many=True).data
        return Response({'count': len(data), 'results': data})

    def _csv(self, qs):
        from io import StringIO
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(['email', 'document_slug', 'document_version', 'accepted_at', 'ip_address', 'user_agent'])
        for a in qs:
            writer.writerow([
                a.user.email,
                a.document.slug,
                a.version,
                a.accepted_at.isoformat() if a.accepted_at else '',
                a.ip_address or '',
                a.user_agent or '',
            ])
        response = HttpResponse(buf.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="legal_acceptances.csv"'
        return response


class LegalComplianceView(APIView):
    """Per-document compliance: accepted_count / total_active_users.

    With the partial UniqueConstraint in place, there is at most one
    active row per slug, so a single ``has_accepted`` Exists per row is
    sufficient — no version-matching needed.
    """
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        required_docs = LegalDocument.objects.filter(
            is_active=True,
            requires_acceptance=True,
            published_at__lte=timezone.now(),
        )
        # "Total active users" = distinct users who have at least one acceptance
        # of any required document (a reasonable denominator for compliance).
        total_active_users = (
            LegalAcceptance.objects.filter(
                document__in=required_docs.values('pk')
            )
            .values('user').distinct().count()
        )
        results = []
        for doc in required_docs:
            accepted_count = LegalAcceptance.objects.filter(
                document=doc,
            ).values('user').distinct().count()
            rate = (accepted_count / total_active_users) if total_active_users else 0.0
            results.append({
                'slug': doc.slug,
                'title': doc.title,
                'version': doc.version,
                'published_at': doc.published_at,
                'accepted_count': accepted_count,
                'acceptance_rate': round(rate, 4),
            })
        return Response({
            'total_active_users': total_active_users,
            'required_documents': results,
        })


class LegalRecentActivityView(APIView):
    """Feed for the admin appbar 'Legal history' dropdown.

    Returns recent acceptances and recent publishes for the dropdown
    body. ``pending_required_count`` was removed in Phase 3 — the
    frontend (Phase 4) drops the badge entirely; this endpoint now
    just provides the activity feed.
    """
    permission_classes = [IsAdminOrSuperUser]

    def get(self, request):
        recent_acceptances = (
            LegalAcceptance.objects.select_related('user', 'document')
            .order_by('-accepted_at')[:10]
        )
        # Newest publish event per slug (so a single re-published slug
        # doesn't fill the dropdown).
        recent_publishes = (
            LegalDocument.objects
            .filter(published_at__isnull=False)
            .order_by('slug', '-published_at')
            .distinct('slug')[:5]
        )
        return Response({
            'recent_acceptances': LegalAcceptanceAdminSerializer(recent_acceptances, many=True).data,
            'recent_publishes': LegalDocumentListSerializer(recent_publishes, many=True).data,
        })

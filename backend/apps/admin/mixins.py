import csv
from io import StringIO

from django.http import StreamingHttpResponse
from django.forms.models import model_to_dict
from rest_framework.filters import SearchFilter

from apps.base.models import AuditAction
from apps.base.throttles import SuperAdminThrottle
from apps.base.utils import log_audit
from apps.admin.permissions import IsSuperUser
from apps.admin.pagination import AdminPagination


class ModelAdminMixin:
    permission_classes = [IsSuperUser]
    throttle_classes = [SuperAdminThrottle]
    pagination_class = AdminPagination
    filter_backends = [SearchFilter]
    search_fields = []

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_CREATE,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_update(self, serializer):
        old = model_to_dict(serializer.instance)
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_UPDATE,
            previous_value=old,
            new_value=model_to_dict(instance),
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_DELETE,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )
        instance.delete()

    def list(self, request, *args, **kwargs):
        if request.query_params.get('export') == 'csv':
            return self._csv_export(request)
        return super().list(request, *args, **kwargs)

    def _csv_export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        if not data:
            return StreamingHttpResponse(
                iter(['']), content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="export.csv"'},
            )

        columns = list(data[0].keys())

        def stream():
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(columns)
            yield buffer.getvalue()
            for row in data:
                buffer = StringIO()
                writer = csv.writer(buffer)
                writer.writerow([
                    str(v) if not isinstance(v, (list, dict)) else str(v)
                    for v in row.values()
                ])
                yield buffer.getvalue()

        filename = getattr(self, 'csv_filename', 'export.csv')
        return StreamingHttpResponse(
            stream(), content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

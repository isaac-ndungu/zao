import csv
from io import StringIO

from django.http import StreamingHttpResponse


class CsvExportMixin:
    csv_filename = 'export.csv'

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
                headers={'Content-Disposition': f'attachment; filename="{self.csv_filename}"'},
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

        return StreamingHttpResponse(
            stream(), content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{self.csv_filename}"'},
        )

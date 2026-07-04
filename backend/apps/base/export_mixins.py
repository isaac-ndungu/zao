import csv
from io import StringIO

from django.http import HttpResponse


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

        buf = StringIO()
        writer = csv.writer(buf)
        if data:
            columns = list(data[0].keys())
            writer.writerow(columns)
            for row in data:
                writer.writerow([
                    str(v) if not isinstance(v, (list, dict)) else str(v)
                    for v in row.values()
                ])

        response = HttpResponse(buf.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.csv_filename}"'
        return response

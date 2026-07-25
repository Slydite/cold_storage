import csv
from django.http import HttpResponse


def csv_response(filename: str, header: list[str], rows: list[list]) -> HttpResponse:
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response

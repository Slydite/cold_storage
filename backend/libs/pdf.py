from django.conf import settings
from django.template.loader import render_to_string


def render_pdf(template_name: str, context: dict, base_url: str | None = None) -> bytes:
    """
    Render a Django HTML template to PDF bytes via WeasyPrint.

    NOTE: WeasyPrint is imported lazily inside this function rather than at top-level.
    On Windows systems, if the GTK3 runtime (libgobject-2.0-0, cairo, pango, etc.) is missing,
    importing weasyprint raises an OSError. Lazily importing it ensures Django management commands
    (e.g., manage.py runserver, migrate) can initialize even if GTK is missing, failing only when
    a PDF render is explicitly requested.
    """
    if base_url is None:
        base_url = str(settings.BASE_DIR)

    import weasyprint

    html_content = render_to_string(template_name, context)
    return weasyprint.HTML(string=html_content, base_url=base_url).write_pdf()

import os

from django.conf import settings
from django.template.loader import render_to_string

# Make font subsetting reproducible.
#
# WeasyPrint embeds subsetted copies of the fonts a document uses, and fontTools
# stamps the subset's `head.modified` field with the CURRENT time. That made two
# renders of the same record differ at byte level -- same stream lengths,
# different bytes -- purely because of an embedded timestamp, with no difference
# in what the document actually shows.
#
# fontTools honours SOURCE_DATE_EPOCH (the reproducible-builds standard) and uses
# it in place of "now", so pinning it makes output genuinely byte-for-byte
# deterministic. This matters because documents are now generated on demand
# rather than stored: the same invoice downloaded twice should be the same file.
#
# Set at import time, and only if the environment has not already chosen a value,
# so a deployment that sets SOURCE_DATE_EPOCH for its own build tooling wins.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1704067200")  # 2024-01-01T00:00:00Z


def render_pdf(template_name: str, context: dict, base_url: str | None = None) -> bytes:
    """
    Render a Django HTML template to PDF bytes via WeasyPrint.

    Output is deterministic: rendering the same context twice returns identical
    bytes (see the SOURCE_DATE_EPOCH note above). Documents are generated on
    demand and never persisted, so determinism is what makes a re-download
    equivalent to the original rather than merely similar.

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

from rest_framework.renderers import BaseRenderer


class PDFRenderer(BaseRenderer):
    """
    Lets DRF's content negotiation accept `Accept: application/pdf`.

    The PDF views return a plain HttpResponse, so this renderer is never
    actually invoked to render anything. It exists because negotiation runs
    in APIView.initial(), *before* the handler: with only JSONRenderer
    configured, a browser asking for application/pdf is rejected with 406
    and the view body never executes. A request with no Accept header
    happens to succeed, which is why this was invisible to tests using the
    Django test client and only showed up in the browser.
    """

    media_type = 'application/pdf'
    format = 'pdf'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class CSVRenderer(BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'
    charset = 'utf-8'
    render_style = 'text'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class XMLRenderer(BaseRenderer):
    media_type = 'application/xml'
    format = 'xml'
    charset = 'utf-8'
    render_style = 'text'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


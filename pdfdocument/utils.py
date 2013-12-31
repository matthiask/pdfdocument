import re

from django.http import HttpResponse

from pdfdocument.document import PDFDocument


FILENAME_RE = re.compile(r'[^A-Za-z0-9\-\.]+')


def pdf_response(filename, as_attachment=True, pdfdocument=PDFDocument,
                 **kwargs):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = '%s; filename="%s.pdf"' % (
        'attachment' if as_attachment else 'inline',
        FILENAME_RE.sub('-', filename),
    )

    return pdfdocument(response, **kwargs), response

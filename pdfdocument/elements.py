import os

from django.conf import settings

from pdfdocument.document import mm


def create_stationery_fn(*fns):
    def _fn(canvas, document):
        for fn in fns:
            fn(canvas, document.PDFDocument)
    return _fn


class ExampleStationery(object):
    def __call__(self, canvas, pdfdocument):
        left_offset = 28.6*mm

        canvas.saveState()
        canvas.setFont('%s-Bold' % pdfdocument.style.fontName, 10)
        canvas.drawString(26*mm, 284*mm, 'PLATA')
        canvas.setFont('%s' % pdfdocument.style.fontName, 10)
        canvas.drawString(26*mm + left_offset, 284*mm, 'Django Shop Software')
        pdfdocument.draw_watermark(canvas)
        canvas.restoreState()

        canvas.saveState()
        canvas.setFont('%s' % pdfdocument.style.fontName, 6)
        for i, text in enumerate(reversed([
                pdfdocument.doc.page_index_string()])):
            canvas.drawRightString(190*mm, (8+3*i)*mm, text)

        for i, text in enumerate(reversed(['PLATA', 'Something'])):
            canvas.drawString(26*mm + left_offset, (8+3*i)*mm, text)

        logo = getattr(settings, 'PDF_LOGO_SETTINGS', None)
        if logo:
            canvas.drawImage(
                os.path.join(
                    settings.APP_BASEDIR,
                    'metronom',
                    'reporting',
                    'images',
                    logo[0]),
                **logo[1])

        canvas.restoreState()


class PageFnWrapper(object):
    """
    Wrap an old-style page setup function
    """

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, canvas, pdfdocument):
        self.fn(canvas, pdfdocument.doc)

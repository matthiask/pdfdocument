# coding=utf-8

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Paragraph, Spacer, Frame,\
    PageTemplate, NextPageTemplate, PageBreak, Table, TableStyle, Image,\
    Preformatted, Flowable, XPreformatted, KeepTogether, CondPageBreak
from reportlab.platypus.flowables import HRFlowable

import os
import copy
from datetime import date, datetime

from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.translation import ugettext as _


pdfmetrics.registerFont(TTFont('Reporting-Regular', os.path.join(
    settings.FONT_PATH, settings.FONT_REGULAR)))
pdfmetrics.registerFont(TTFont('Reporting-Italic', os.path.join(
    settings.FONT_PATH, settings.FONT_ITALIC)))
pdfmetrics.registerFont(TTFont('Reporting-Bold', os.path.join(
    settings.FONT_PATH, settings.FONT_BOLD)))
pdfmetrics.registerFont(TTFont('Reporting-BoldItalic', os.path.join(
    settings.FONT_PATH, settings.FONT_BOLDITALIC)))
addMapping('Reporting-Regular', 0, 0, 'Reporting-Regular') # regular
addMapping('Reporting-Regular', 0, 1, 'Reporting-Italic') # italic
addMapping('Reporting-Regular', 1, 0, 'Reporting-Bold') # bold
addMapping('Reporting-Regular', 1, 1, 'Reporting-BoldItalic') # bold & italic


class Empty(object):
    pass


def sanitize(text):
    REPLACE_MAP = [ (u'&', '&#38;'),
                    (u'<', '&#60;'),
                    (u'>', '&#62;'),
                    (u'ç', '&#231;'),
                    (u'Ç', '&#199;'),
                    (u'\n', '<br />'),
                    (u'\r', ''), ]

    for p, q in REPLACE_MAP:
        text = text.replace(p, q)
    return text


_Paragraph = Paragraph

def MarkupParagraph(txt, *args, **kwargs):
    if not txt: return _Paragraph(u'', *args, **kwargs)
    return _Paragraph(txt, *args, **kwargs)


def Paragraph(txt, *args, **kwargs):
    if not txt: return _Paragraph(u'', *args, **kwargs)
    return _Paragraph(sanitize(txt), *args, **kwargs)


class BottomTable(Table):
    """
    This table will automatically be moved to the bottom of the page using the
    BottomSpacer right before it.
    """
    pass


class BottomSpacer(Spacer):
    def wrap(self, availWidth, availHeight):
        my_height = availHeight-self._doc.bottomTableHeight

        if my_height<=0:
            return (self.width, availHeight)
        else:
            return (self.width, my_height)


class RestartPageBreak(PageBreak):
    """
    Insert a page break and restart the page numbering.
    """
    pass


class ReportingDocTemplate(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        BaseDocTemplate.__init__(self, *args, **kwargs)
        self.bottomTableHeight = 0
        self.bottomTableIsLast = False
        self.numPages = 0
        self._lastNumPages = 0
        self.setProgressCallBack(self._onProgress_cb)

        # For batch reports with several PDFs concatenated
        self.restartDoc = False
        self.restartDocIndex = 0
        self.restartDocPageNumbers = []

    def afterFlowable(self, flowable):
        self.numPages = max(self.canv.getPageNumber(), self.numPages)
        self.bottomTableIsLast = False

        if isinstance(flowable, BottomTable):
            self.bottomTableHeight = reduce(
                lambda p, q: p+q,
                flowable._rowHeights,
                0)

            self.bottomTableIsLast = True

        elif isinstance(flowable, RestartPageBreak):
            self.restartDoc = True
            self.restartDocIndex += 1
            self.restartDocPageNumbers.append(self.page)

    # here the real hackery starts ... thanks Ralph
    def _allSatisfied(self):
        """ Called by multi-build - are all cross-references resolved? """
        if self._lastnumPages < self.numPages:
            return 0
        return BaseDocTemplate._allSatisfied(self)

    def _onProgress_cb(self, what, arg):
        if what=='STARTED':
            self._lastnumPages = self.numPages
            self.restartDocIndex = 0
            #self.restartDocPageNumbers = []

    def page_index_string(self):
        """
        Return page index string for the footer.

        This is the ugliest thing I've done in the last two years.
        For this I'll burn in programmer hell.

        At least it is contained here.

        (Determining the total number of pages in reportlab is a mess anyway...)
        """

        current_page = self.page
        total_pages = self.numPages

        if self.restartDoc:
            if self.restartDocIndex:
                current_page = current_page - self.restartDocPageNumbers[self.restartDocIndex-1] + 1
                if len(self.restartDocPageNumbers) > self.restartDocIndex:
                    total_pages = self.restartDocPageNumbers[self.restartDocIndex] - self.restartDocPageNumbers[self.restartDocIndex-1] + 1
            else:
                total_pages = self.restartDocPageNumbers[0]

        if self.bottomTableHeight:
            total_pages -= 1

            if self.bottomTableIsLast and current_page==1:
                total_pages = max(1, total_pages-1)

        return _('Page %(current_page)d of %(total_pages)d') % {
            'current_page': current_page, 'total_pages': total_pages}


def reporting_pdf_draw_page_template(c, doc):
    doc.PDFDocument.header(c, settings.REPORTING_PDF_HEADER)
    doc.PDFDocument.footer(c, (
        doc.page_index_string(),
        ))


class PDFDocument(object):
    show_boundaries = False
    _watermark = None

    def __init__(self, *args, **kwargs):
        self.doc = ReportingDocTemplate(*args, **kwargs)
        self.doc.PDFDocument = self
        self.story = []

    def generate_style(self, base_size):
        self.style = Empty()
        self.style.baseSize = base_size

        _styles = getSampleStyleSheet()

        self.style.normal = _styles['Normal']
        self.style.normal.fontName = 'Reporting-Regular'
        self.style.normal.fontSize = base_size
        self.style.normal.firstLineIndent = 0
        #normal.textColor = '#0e2b58'

        self.style.heading1 = copy.deepcopy(self.style.normal)
        self.style.heading1.fontName = 'Reporting-Regular'
        self.style.heading1.fontSize = 1.5*base_size
        self.style.heading1.leading = 2*base_size
        #heading1.leading = 10*mm

        self.style.heading2 = copy.deepcopy(self.style.normal)
        self.style.heading2.fontName = 'Reporting-Bold'
        self.style.heading2.fontSize = 1.25*base_size
        self.style.heading2.leading = 1.75*base_size
        #heading2.leading = 5*mm

        self.style.heading3 = copy.deepcopy(self.style.normal)
        self.style.heading3.fontName = 'Reporting-Bold'
        self.style.heading3.fontSize = 1.1*base_size
        self.style.heading3.leading = 1.5*base_size
        self.style.heading3.textColor = '#666666'
        #heading3.leading = 5*mm

        self.style.small = copy.deepcopy(self.style.normal)
        self.style.small.fontSize = base_size-0.9

        self.style.smaller = copy.deepcopy(self.style.normal)
        self.style.smaller.fontSize = base_size*0.75

        self.style.bold = copy.deepcopy(self.style.normal)
        self.style.bold.fontName = 'Reporting-Bold'

        self.style.boldr = copy.deepcopy(self.style.bold)
        self.style.boldr.alignment = TA_RIGHT

        self.style.right = copy.deepcopy(self.style.normal)
        self.style.right.alignment = TA_RIGHT

        self.style.indented = copy.deepcopy(self.style.normal)
        self.style.indented.leftIndent = 0.5*cm

        self.style.tablenotes = copy.deepcopy(self.style.indented)
        self.style.tablenotes.fontName = 'Reporting-Italic'

        # alignment = TA_RIGHT
        # leftIndent = 0.4*cm
        # spaceBefore = 0
        # spaceAfter = 0

        self.style.tableBase = (
            ('FONT', (0, 0), (-1, -1), 'Reporting-Regular', base_size),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('FIRSTLINEINDENT', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            )

        self.style.table = self.style.tableBase+(
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            )

        self.style.tableLLR = self.style.tableBase+(
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, 0), 'BOTTOM'),
            )

        self.style.tableHead = self.style.tableBase+(
            ('FONT', (0, 0), (-1, 0), 'Reporting-Bold', base_size),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, 0), (-1, 0), 0.2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.2, colors.black),
            )

        self.style.tableOptional = self.style.tableBase+(
                ('FONT', (0, 0), (-1, 0), 'Reporting-Italic', self.style.baseSize),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (1, 0), (-1, -1), 2*cm),
                )

    def init_templates(self, page_fn, page_fn_later=None):
        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[self.frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[self.frame], onPage=page_fn_later or page_fn),
            ])
        self.story.append(NextPageTemplate('Later'))

    def init_report(self, page_fn=reporting_pdf_draw_page_template, page_fn_later=None):
        frame_kwargs = {'showBoundary': self.show_boundaries,
            'leftPadding': 0, 'rightPadding': 0, 'topPadding': 0, 'bottomPadding': 0}

        full_frame = Frame(2.6*cm, 2*cm, 16.4*cm, 25*cm, **frame_kwargs)

        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[full_frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[full_frame], onPage=page_fn_later or page_fn),
            ])
        self.story.append(NextPageTemplate('Later'))

        self.generate_style(8)

    def init_confidential_report(self, page_fn=reporting_pdf_draw_page_template, page_fn_later=None):
        if not page_fn_later:
            page_fn_later = page_fn

        def _first_page_fn(canvas, doc):
            page_fn(canvas, doc)
            doc.PDFDocument.confidential(canvas)
            doc.PDFDocument.watermark('CONFIDENTIAL')

        self.init_report(page_fn=_first_page_fn, page_fn_later=page_fn_later)

    def init_letter(self, page_fn=reporting_pdf_draw_page_template, page_fn_later=None):
        frame_kwargs = {'showBoundary': self.show_boundaries,
            'leftPadding': 0, 'rightPadding': 0, 'topPadding': 0, 'bottomPadding': 0}

        address_frame = Frame(2.6*cm, settings.REPORTING_PDF_ADDRESSBLOCK_Y, 16.4*cm, 4*cm, **frame_kwargs)
        rest_frame = Frame(2.6*cm, 2*cm, 16.4*cm, 18.2*cm, **frame_kwargs)
        full_frame = Frame(2.6*cm, 2*cm, 16.4*cm, 25*cm, **frame_kwargs)

        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[address_frame, rest_frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[full_frame], onPage=page_fn_later or page_fn),
            ])
        self.story.append(NextPageTemplate('Later'))

        self.generate_style(9)

    def watermark(self, watermark=None):
        self._watermark = watermark

    def restart(self):
        self.story.append(NextPageTemplate('First'))
        self.story.append(RestartPageBreak())

    def p(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.normal))

    def h1(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.heading1))

    def h2(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.heading2))

    def h3(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.heading3))

    def small(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.small))

    def smaller(self, text, style=None):
        self.story.append(Paragraph(text, style or self.style.smaller))

    def p_markup(self, text, style=None):
        self.story.append(MarkupParagraph(text, style or self.style.normal))

    def spacer(self, height=0.6*cm):
        self.story.append(Spacer(1, height))

    def table(self, data, columns, style=None):
        self.story.append(Table(data, columns, style=style or self.style.table))

    def hr(self):
        self.story.append(HRFlowable(width='100%', thickness=0.2, color=colors.black))

    def hr_mini(self):
        self.story.append(HRFlowable(width='100%', thickness=0.2, color=colors.grey))

    def pagebreak(self):
        self.story.append(PageBreak())

    def bottom_table(self, data, columns, style=None):
        obj = BottomSpacer(1, 1)
        obj._doc = self.doc
        self.story.append(obj)

        self.story.append(BottomTable(data, columns, style=style or self.style.table))

    def generate(self):
        self.doc.multiBuild(self.story)

    def confidential(self, canvas):
        canvas.saveState()

        canvas.translate(18.5*cm, 27.4*cm)

        canvas.setLineWidth(3)
        canvas.setFillColorRGB(1, 0, 0)
        canvas.setStrokeGray(0.5)

        p = canvas.beginPath()
        p.moveTo(10, 0)
        p.lineTo(20, 10)
        p.lineTo(30, 0)
        p.lineTo(40, 10)
        p.lineTo(30, 20)
        p.lineTo(40, 30)
        p.lineTo(30, 40)
        p.lineTo(20, 30)
        p.lineTo(10, 40)
        p.lineTo(0, 30)
        p.lineTo(10, 20)
        p.lineTo(0, 10)

        canvas.drawPath(p, fill=1, stroke=0)

        canvas.restoreState()

    def header(self, canvas, text):
        canvas.saveState()
        canvas.setFont('Reporting-Bold', 10)
        canvas.drawString(26*mm, 284*mm, text[0])
        canvas.setFont('Reporting-Regular', 10)
        canvas.drawString(26*mm+settings.REPORTING_PDF_LEFT_OFFSET, 284*mm, text[1])

        if self._watermark:
            canvas.rotate(60)
            canvas.setFillColorRGB(0.97, 0.97, 0.97)
            canvas.setFont('Reporting-Regular', 120)
            canvas.drawCentredString(195*mm, -30*mm, self._watermark)

        canvas.restoreState()

    def footer(self, canvas, texts):
        canvas.saveState()
        canvas.setFont('Reporting-Regular', 6)
        for i, text in enumerate(reversed(texts)):
            canvas.drawRightString(190*mm, (8+3*i)*mm, text)

        for i, text in enumerate(reversed(settings.REPORTING_PDF_FOOTER)):
            canvas.drawString(26*mm+settings.REPORTING_PDF_LEFT_OFFSET, (8+3*i)*mm, text)

        logo = getattr(settings, 'PDF_LOGO_SETTINGS', None)
        if logo:
            canvas.drawImage(os.path.join(settings.APP_BASEDIR, 'metronom', 'reporting', 'images', logo[0]),
                **logo[1])

        canvas.restoreState()

    def next_frame(self):
        self.story.append(CondPageBreak(20*cm))

    def start_keeptogether(self):
        self.keeptogether_index = len(self.story)

    def end_keeptogether(self):
        keeptogether = KeepTogether(self.story[self.keeptogether_index:])
        self.story = self.story[:self.keeptogether_index]
        self.story.append(keeptogether)

    def address_head(self):
        self.smaller(settings.REPORTING_PDF_ADDRESSLINE)
        self.spacer(2*mm)

    def address(self, obj, prefix=''):
        data = {}
        for field in ('company', 'manner_of_address', 'first_name', 'last_name', 'address', 'zip_code', 'city'):
            data[field] = getattr(obj, '%s%s' % (prefix, field))

        address = []
        if data['company']:
            address.append(data['company'])

        title = data['manner_of_address'] and '%s ' % data['manner_of_address'] or ''
        if data['first_name']:
            address.append(u'%s%s %s' % (title, data['first_name'], data['last_name']))
        else:
            address.append(u'%s%s' % (title, data['last_name']))

        address.append(data['address'])
        address.append(u'%s %s' % (data['zip_code'], data['city']))

        self.p('\n'.join(address))

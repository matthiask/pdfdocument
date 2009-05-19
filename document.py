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

import os
import copy
from datetime import date, datetime

from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.html import escape


pdfmetrics.registerFont(TTFont('ReportingRegular', os.path.join(
    settings.FONT_PATH, settings.FONT_REGULAR)))
pdfmetrics.registerFont(TTFont('ReportingBold', os.path.join(
    settings.FONT_PATH, settings.FONT_BOLD)))
addMapping('Reporting', 0, 0, 'ReportingRegular') # regular
addMapping('Reporting', 0, 1, 'ReportingRegular') # italic
addMapping('Reporting', 1, 0, 'ReportingBold') # bold
addMapping('Reporting', 1, 1, 'ReportingBold') # bold & italic


class Style(object):
    _styles = getSampleStyleSheet()

    normal = _styles['Normal']
    normal.fontName = 'ReportingRegular'
    normal.fontSize = 8
    normal.firstLineIndent = 0
    #normal.textColor = '#0e2b58'

    heading1 = copy.deepcopy(normal)
    heading1.fontName = 'ReportingRegular'
    heading1.fontSize = 12
    heading1.leading = 16
    #heading1.leading = 10*mm

    heading2 = copy.deepcopy(normal)
    heading2.fontName = 'ReportingBold'
    heading2.fontSize = 10
    heading2.leading = 14
    #heading2.leading = 5*mm

    small = copy.deepcopy(normal)
    small.fontSize = 8

    smaller = copy.deepcopy(normal)
    smaller.fontSize = 6

    bold = copy.deepcopy(normal)
    bold.fontName = 'ReportingBold'

    boldr = copy.deepcopy(bold)
    boldr.alignment = TA_RIGHT

    right = copy.deepcopy(normal)
    right.alignment = TA_RIGHT

    indented = copy.deepcopy(normal)
    indented.leftIndent = 0.3*cm

    # alignment = TA_RIGHT
    # leftIndent = 0.4*cm
    # spaceBefore = 0
    # spaceAfter = 0

    tableBase = (
        ('FONT', (0, 0), (-1, -1), 'ReportingRegular', 8),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('FIRSTLINEINDENT', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        )

    table = tableBase+(
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        )

    tableLLR = tableBase+(
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, 0), 'BOTTOM'),
        )

    tableHead = tableBase+(
        ('FONT', (0, 0), (-1, 0), 'ReportingBold', 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEABOVE', (0, 0), (-1, 0), 0.2, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.2, colors.black),
        )


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
            return (self.width, my_height-10)


class ReportingDocTemplate(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        BaseDocTemplate.__init__(self, *args, **kwargs)
        self.bottomTableHeight = 0
        self.numPages = 0
        self._lastNumPages = 0
        self.setProgressCallBack(self._onProgress_cb)

    def afterFlowable(self, flowable):
        self.numPages = max(self.canv.getPageNumber(), self.numPages)

        if isinstance(flowable, BottomTable):
            self.bottomTableHeight = reduce(
                lambda p, q: p+q,
                flowable._rowHeights,
                0)

            # evil hack... I don't exactly know why this is necessary (mk)
            self.numPages -= 1

    # here the real hackery starts ... thanks Ralph
    def _allSatisfied(self):
        """ Called by multi-build - are all cross-references resolved? """
        if self._lastnumPages < self.numPages:
            return 0
        return BaseDocTemplate._allSatisfied(self)

    def _onProgress_cb(self, what, arg):
        if what=='STARTED':
            self._lastnumPages = self.numPages


class PDFDocument(object):
    show_boundaries = False

    def __init__(self, *args, **kwargs):
        self.doc = ReportingDocTemplate(*args, **kwargs)
        self.doc.PDFDocument = self
        #self.doc.setProgressCallBack(self.__progresshandler)
        self.story = []

    def init_frames(self):
        self.frame = Frame(2.6*cm, 2*cm, 16.4*cm, 25*cm, showBoundary=self.show_boundaries)

    def init_templates(self, page_fn, page_fn_later=None):
        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[self.frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[self.frame], onPage=page_fn_later or page_fn),
            ])
        self.story.append(NextPageTemplate('Later'))

    def _p(default_style):
        def _fn(self, text=u'', style=None):
            self.story.append(Paragraph(text, style or default_style))
        return _fn

    p = _p(Style.normal)
    h1 = _p(Style.heading1)
    h2 = _p(Style.heading2)
    small = _p(Style.small)
    smaller = _p(Style.smaller)

    def p_markup(self, text, style=None):
        self.story.append(MarkupParagraph(text, style or Style.normal))

    def spacer(self, height=0.6*cm):
        self.story.append(Spacer(1, height))

    def table(self, data, columns, style=None):
        self.story.append(Table(data, columns, style=style or Style.table))

    def hr(self):
        self.story.append(HRFlowable(width='100%', thickness=0.2, color=black))

    def pagebreak(self):
        self.story.append(PageBreak())

    def bottom_table(self, data, columns, style=None):
        obj = BottomSpacer(1, 1)
        obj._doc = self.doc
        self.story.append(obj)

        self.story.append(BottomTable(data, columns, style=style or Style.table))

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
        canvas.setFont('ReportingRegular', 10)
        canvas.drawString(26*mm, 284*mm, text)
        canvas.restoreState()

    def footer(self, canvas, texts):
        canvas.saveState()
        canvas.setFont('ReportingRegular', 6)
        for i, text in enumerate(reversed(texts)):
            canvas.drawString(26*mm, (8+3*i)*mm, text)
        canvas.restoreState()

    def next_frame(self):
        self.story.append(CondPageBreak(20*cm))


REPORTING_PDF_PAGE_WIDTH = 164*mm
REPORTING_PDF_LEFT_OFFSET = 28.6*mm


def reporting_pdf_draw_page_template(c, doc):
    doc.PDFDocument.header(c, u'FEINHEIT GmbH')
    doc.PDFDocument.footer(c, (
        _('Page %(current_page)d of %(total_pages)d') % {
        'current_page': doc.page, 'total_pages': doc.numPages},
        ))

    c.drawImage(
        os.path.join(settings.APP_BASEDIR, 'base', 'reporting', 'images', 'feinheit_logo_15_30_mini.png'),
        x=26*mm,
        y=9.2*mm,
        width=0.95*REPORTING_PDF_LEFT_OFFSET,
        height=0.95*REPORTING_PDF_LEFT_OFFSET/8.395,
        )


class ReportingPDFDocument(PDFDocument):
    def init_letter(self, page_fn=reporting_pdf_draw_page_template, page_fn_later=None):
        frame_kwargs = {'showBoundary': self.show_boundaries,
            'leftPadding': 0, 'rightPadding': 0, 'topPadding': 0, 'bottomPadding': 0}

        address_frame = Frame(2.6*cm, 22*cm, 16.4*cm, 4*cm, **frame_kwargs)
        rest_frame = Frame(2.6*cm, 2*cm, 16.4*cm, 20*cm, **frame_kwargs)
        full_frame = Frame(2.6*cm, 2*cm, 16.4*cm, 25*cm, **frame_kwargs)

        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[address_frame, rest_frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[full_frame], onPage=page_fn_later or page_fn),
            ])
        self.story.append(NextPageTemplate('Later'))

    def address_head(self):
        self.smaller(u'FEINHEIT GmbH · Dienerstrasse 15 · CH-8004 Zürich')
        self.spacer(2*mm)

    def address(self, obj, prefix):
        data = {}
        for field in ('company', 'first_name', 'last_name', 'address', 'zip_code', 'city'):
            data[field] = getattr(obj, '%s_%s' % (prefix, field))

        address = []
        if data['company']:
            address.append(data['company'])
        if data['first_name']:
            address.append(u'%s %s' % (data['first_name'], data['last_name']))
        else:
            address.append(data['last_name'])
        address.append(data['address'])
        address.append(u'%s %s' % (data['zip_code'], data['city']))

        self.p('\n'.join(address))

    def payment_info(self, invoice, bankaccount):
        self.bottom_table((
                (u'Bitte überweisen Sie obenstehenden Betrag innerhalb von %s Tagen (%s) auf folgendes Konto:' % (
                    invoice.payment_within, invoice.due_date.strftime('%d.%m.%Y')), ''),
                ('', ''),
                (u'Bank', bankaccount.bank),
                (u'Kontonummer', bankaccount.account),
                (u'Bankenclearingnr.', bankaccount.clearing_nr),
                (u'IBAN-Nr.', bankaccount.iban),
                (u'BIC/SWIFT', bankaccount.bic),
            ),
            (REPORTING_PDF_LEFT_OFFSET, REPORTING_PDF_PAGE_WIDTH-REPORTING_PDF_LEFT_OFFSET),
            style=Style.tableLLR+(
                ('SPAN', (0, 0), (-1, 0)),
                ('FONT', (0, 0), (-1, 0), 'ReportingBold', 8),
                )
            )

    def header(self, canvas, text):
        canvas.saveState()
        canvas.setFont('ReportingBold', 10)
        canvas.drawString(26*mm, 284*mm, u'FEINHEIT GmbH')
        canvas.setFont('ReportingRegular', 10)
        canvas.drawString(26*mm+REPORTING_PDF_LEFT_OFFSET, 284*mm, u'kreativ studio Zürich')
        canvas.restoreState()


    def footer(self, canvas, texts):
        canvas.saveState()
        canvas.setFont('ReportingRegular', 6)
        for i, text in enumerate(reversed(texts)):
            canvas.drawRightString(190*mm, (8+3*i)*mm, text)

        canvas.drawString(26*mm+REPORTING_PDF_LEFT_OFFSET, 11*mm, u'FEINHEIT GmbH · Dienerstrasse 15 · CH-8004 Zürich · www.feinheit.ch')
        canvas.drawString(26*mm+REPORTING_PDF_LEFT_OFFSET, 8*mm, u'+41 55 511 11 41 · kontakt@feinheit.ch · MwSt: 681 875')
        canvas.restoreState()

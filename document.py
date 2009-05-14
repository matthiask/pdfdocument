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
    Preformatted, Flowable, XPreformatted

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
    #normal.leading = 2.8*mm
    #normal.textColor = '#0e2b58'

    heading1 = copy.deepcopy(normal)
    heading1.fontName = 'ReportingRegular'
    heading1.fontSize = 18
    #heading1.leading = 10*mm

    heading2 = copy.deepcopy(normal)
    heading2.fontName = 'ReportingBold'
    heading2.fontSize = 14
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
        ('FONT', (0, 0), (-1, -1), 'ReportingBold', 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEABOVE', (0, 0), (-1, 0), 0.2, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.2, colors.black),
        )

_Paragraph = Paragraph
def Paragraph(txt, *args, **kwargs):
    if not txt: return _Paragraph(u'', *args, **kwargs)
    return _Paragraph(force_unicode(escape(txt)), *args, **kwargs)


class PDFDocument(object):
    show_boundaries = False

    def __init__(self, *args, **kwargs):
        self.doc = BaseDocTemplate(*args, **kwargs)
        self.numPages = 0
        self.doc._allSatisfied=self.__all_satisfied
        self.doc.setProgressCallBack(self.__progresshandler)
        self.doc.afterPage=self.__after_page
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
            self.story.append(Paragraph(text), style or default_style)

    p = _p(Style.normal)
    h1 = _p(Style.heading1)
    h2 = _p(Style.heading2)
    small = _p(Style.small)
    smaller = _p(Style.smaller)

    def spacer(self, height=0.6*cm):
        self.story.append(Spacer(1, height))

    def table(self, data, columns, style=None):
        self.story.append(Table(data, columns, style=style or Style.table))

    def hr(self):
        self.story.append(HRFlowable(width='100%', thickness=0.2, color=black))

    def generate(self):
        self.doc.multiBuild(self.story)

    def __after_page(self):
        """This is called after page processing, and
        immediately after the afterDrawPage method
        of the current page template."""
        self.numPages = max(self.doc.canv.getPageNumber(), self.numPages)

    def __all_satisfied(self):
        """ Called by multi-build - are all cross-references resolved? """
        if self._lastnumPages < self.numPages:
            return 0
        return BaseDocTemplate._allSatisfied(self.doc)

    def __progresshandler(self, what, arg):
        """ follow the progress """
        if what=='STARTED':
            self._lastnumPages = self.numPages

            # reset story
            self.story = []

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

# coding=utf-8

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
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


class Empty(object):
    pass


def save_canvas_state(func, *args, **kwargs):
    def _func(c, *args, **kwargs):
        c.saveState()
        func(c, *args, **kwargs)
        c.restoreState()
    return _func


pdfmetrics.registerFont(TTFont('ReportingRegular', os.path.join(
    settings.FONT_PATH, settings.FONT_REGULAR)))
pdfmetrics.registerFont(TTFont('ReportingBold', os.path.join(
    settings.FONT_PATH, settings.FONT_BOLD)))


_Paragraph = Paragraph
def Paragraph(txt, *args, **kwargs):
    if not txt: return _Paragraph(u'', *args, **kwargs)
    return _Paragraph(force_unicode(escape(txt)), *args, **kwargs)


class PDFDocument(object):
    style = Empty()
    story = []
    show_boundary = False

    def __init__(self, *args, **kwargs):
        self.doc = BaseDocTemplate(*args, **kwargs)
        self.numPages = 0
        self.doc._allSatisfied=self.__all_satisfied
        self.doc.setProgressCallBack(self.__progresshandler)
        self.doc.afterPage=self.__after_page
        self.story = []

    def _process_text(self, text):
        return force_unicode(escape(text))

    def init_styles(self):
        self._styles = getSampleStyleSheet()

        self.style.normal = self._styles['Normal']
        self.style.normal.fontName = 'ReportingRegular'
        self.style.normal.fontSize = 8
        #self.style.normal.leading = 2.8*mm
        #self.style.normal.textColor = '#0e2b58'

        self.style.heading1 = copy.deepcopy(self.style.normal)
        self.style.heading1.fontName = 'ReportingRegular'
        self.style.heading1.fontSize = 18
        #self.style.heading1.leading = 10*mm

        self.style.heading2 = copy.deepcopy(self.style.normal)
        self.style.heading2.fontName = 'ReportingBold'
        self.style.heading2.fontSize = 14
        #self.style.heading2.leading = 5*mm

        self.style.small = copy.deepcopy(self.style.normal)
        self.style.small.fontSize = 8

        self.style.smaller = copy.deepcopy(self.style.normal)
        self.style.smaller.fontSize = 6

        self.style.bold = copy.deepcopy(self.style.normal)
        self.style.bold.fontName = 'ReportingBold'

        self.style.boldr = copy.deepcopy(self.style.bold)
        self.style.boldr.alignment = TA_RIGHT

        self.style.right = copy.deepcopy(self.style.normal)
        self.style.right.alignment = TA_RIGHT

        # style.alignment = TA_RIGHT
        # style.leftIndent = 0.4*cm
        # style.spaceBefore = 0
        # style.spaceAfter = 0

        self.style.table = (
            ('FONT', (0, 0), (-1, -1), 'ReportingRegular', 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            )

        self.style.tableLLR = (
            ('FONT', (0, 0), (-1, -1), 'ReportingRegular', 8),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, 0), 'BOTTOM'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            )

        self.style.tableHead = (
            ('FONT', (0, 0), (-1, -1), 'ReportingBold', 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('LINEABOVE', (0, 0), (-1, 0), 0.2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.2, colors.black),
            )

    def init_frame(self):
        self.frame = Frame(2.6*cm, 2*cm, 16.4*cm, 25*cm, showBoundary=self.show_boundary)

    def setup_single_page(self, page_fn, page_fn_later=None):
        self.doc.addPageTemplates([
            PageTemplate(id='First', frames=[self.frame], onPage=page_fn),
            PageTemplate(id='Later', frames=[self.frame], onPage=page_fn_later and page_fn_later or page_fn),
            ])

    def p(self, text=u'', style=None):
        if style is None:
            style = self.style.normal
        self.story.append(Paragraph(self._process_text(text), style))

    def h1(self, text=u''):
        self.story.append(Paragraph(self._process_text(text), self.style.heading1))

    def h2(self, text=u''):
        self.story.append(Paragraph(self._process_text(text), self.style.heading2))

    def small(self, text=u''):
        self.story.append(Paragraph(self._process_text(text), self.style.small))

    def smaller(self, text=u''):
        self.story.append(Paragraph(self._process_text(text), self.style.smaller))

    def spacer(self, height=0.6*cm):
        self.story.append(Spacer(1, height))

    def table(self, data, columns, style=None):
        if style is None:
            style = self.style.table
        self.story.append(Table(data, columns, style=style))

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

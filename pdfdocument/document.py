# coding=utf-8

import copy
import sys
import unicodedata
from functools import reduce

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.fonts import addMapping
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph as _Paragraph,
    Spacer,
    Table,
)
from reportlab.platypus.flowables import HRFlowable


PY2 = sys.version_info[0] < 3

if PY2:
    string_type = unicode  # noqa
else:
    string_type = str


def register_fonts_from_paths(
    regular, italic=None, bold=None, bolditalic=None, font_name="Reporting"
):
    """
    Pass paths to TTF files which should be used for the PDFDocument
    """

    pdfmetrics.registerFont(TTFont("%s" % font_name, regular))
    pdfmetrics.registerFont(TTFont("%s-Italic" % font_name, italic or regular))
    pdfmetrics.registerFont(TTFont("%s-Bold" % font_name, bold or regular))
    pdfmetrics.registerFont(
        TTFont("%s-BoldItalic" % font_name, bolditalic or bold or regular)
    )

    addMapping("%s" % font_name, 0, 0, "%s" % font_name)
    addMapping("%s" % font_name, 0, 1, "%s-Italic" % font_name)
    addMapping("%s" % font_name, 1, 0, "%s-Bold" % font_name)
    addMapping("%s" % font_name, 1, 1, "%s-BoldItalic" % font_name)


class Empty(object):
    pass


def sanitize(text):
    REPLACE_MAP = [
        (u"&", "&#38;"),
        (u"<", "&#60;"),
        (u">", "&#62;"),
        (u"ç", "&#231;"),
        (u"Ç", "&#199;"),
        (u"\n", "<br />"),
        (u"\r", ""),
    ]

    for p, q in REPLACE_MAP:
        text = text.replace(p, q)
    return text


def normalize(text):
    """
    Some layers of reportlab, PDF or font handling or whatever cannot handle
    german umlauts in decomposed form correctly. Normalize everything to
    NFKC.
    """
    if not isinstance(text, string_type):
        text = string_type(text)
    return unicodedata.normalize("NFKC", text)


def MarkupParagraph(txt, *args, **kwargs):
    if not txt:
        return _Paragraph(u"", *args, **kwargs)
    return _Paragraph(normalize(txt), *args, **kwargs)


def Paragraph(txt, *args, **kwargs):
    if not txt:
        return _Paragraph(u"", *args, **kwargs)
    return _Paragraph(sanitize(normalize(txt)), *args, **kwargs)


class BottomTable(Table):
    """
    This table will automatically be moved to the bottom of the page using the
    BottomSpacer right before it.
    """

    pass


class BottomSpacer(Spacer):
    def wrap(self, availWidth, availHeight):
        my_height = availHeight - self._doc.bottomTableHeight

        if my_height <= 0:
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
            self.bottomTableHeight = reduce(lambda p, q: p + q, flowable._rowHeights, 0)

            self.bottomTableIsLast = True

        elif isinstance(flowable, RestartPageBreak):
            self.restartDoc = True
            self.restartDocIndex += 1
            self.restartDocPageNumbers.append(self.page)

    # here the real hackery starts ... thanks Ralph
    def _allSatisfied(self):
        """ Called by multi-build - are all cross-references resolved? """
        if self._lastNumPages < self.numPages:
            return 0
        return BaseDocTemplate._allSatisfied(self)

    def _onProgress_cb(self, what, arg):
        if what == "STARTED":
            self._lastNumPages = self.numPages
            self.restartDocIndex = 0
            # self.restartDocPageNumbers = []

    def page_index(self):
        """
        Return the current page index as a tuple (current_page, total_pages)

        This is the ugliest thing I've done in the last two years.
        For this I'll burn in programmer hell.

        At least it is contained here.

        (Determining the total number of pages in reportlab is a mess
        anyway...)
        """

        current_page = self.page
        total_pages = self.numPages

        if self.restartDoc:
            if self.restartDocIndex:
                current_page = (
                    current_page
                    - self.restartDocPageNumbers[self.restartDocIndex - 1]
                    + 1
                )
                if len(self.restartDocPageNumbers) > self.restartDocIndex:
                    total_pages = (
                        self.restartDocPageNumbers[self.restartDocIndex]
                        - self.restartDocPageNumbers[self.restartDocIndex - 1]
                        + 1
                    )
            else:
                total_pages = self.restartDocPageNumbers[0]

        if self.bottomTableHeight:
            total_pages -= 1

            if self.bottomTableIsLast and current_page == 1:
                total_pages = max(1, total_pages)

        # Ensure total pages is always at least 1
        total_pages = max(1, total_pages)

        return (current_page, total_pages)

    def page_index_string(self):
        """
        Return page index string for the footer.
        """
        current_page, total_pages = self.page_index()

        return self.PDFDocument.page_index_string(current_page, total_pages)


def dummy_stationery(c, doc):
    pass


class PDFDocument(object):
    show_boundaries = False
    _watermark = None

    def __init__(self, *args, **kwargs):
        self.doc = ReportingDocTemplate(*args, **kwargs)
        self.doc.PDFDocument = self
        self.story = []

        self.font_name = kwargs.get("font_name", "Helvetica")
        self.font_size = kwargs.get("font_size", 9)

    def page_index_string(self, current_page, total_pages):
        return "Page %(current_page)d of %(total_pages)d" % {
            "current_page": current_page,
            "total_pages": total_pages,
        }

    def generate_style(self, font_name=None, font_size=None):
        self.style = Empty()
        self.style.fontName = font_name or self.font_name
        self.style.fontSize = font_size or self.font_size

        _styles = getSampleStyleSheet()

        self.style.normal = _styles["Normal"]
        self.style.normal.fontName = "%s" % self.style.fontName
        self.style.normal.fontSize = self.style.fontSize
        self.style.normal.firstLineIndent = 0
        # normal.textColor = '#0e2b58'

        self.style.heading1 = copy.deepcopy(self.style.normal)
        self.style.heading1.fontName = "%s" % self.style.fontName
        self.style.heading1.fontSize = 1.5 * self.style.fontSize
        self.style.heading1.leading = 2 * self.style.fontSize
        # heading1.leading = 10*mm

        self.style.heading2 = copy.deepcopy(self.style.normal)
        self.style.heading2.fontName = "%s-Bold" % self.style.fontName
        self.style.heading2.fontSize = 1.25 * self.style.fontSize
        self.style.heading2.leading = 1.75 * self.style.fontSize
        # heading2.leading = 5*mm

        self.style.heading3 = copy.deepcopy(self.style.normal)
        self.style.heading3.fontName = "%s-Bold" % self.style.fontName
        self.style.heading3.fontSize = 1.1 * self.style.fontSize
        self.style.heading3.leading = 1.5 * self.style.fontSize
        self.style.heading3.textColor = "#666666"
        # heading3.leading = 5*mm

        self.style.small = copy.deepcopy(self.style.normal)
        self.style.small.fontSize = self.style.fontSize - 0.9

        self.style.smaller = copy.deepcopy(self.style.normal)
        self.style.smaller.fontSize = self.style.fontSize * 0.75

        self.style.bold = copy.deepcopy(self.style.normal)
        self.style.bold.fontName = "%s-Bold" % self.style.fontName

        self.style.boldr = copy.deepcopy(self.style.bold)
        self.style.boldr.alignment = TA_RIGHT

        self.style.right = copy.deepcopy(self.style.normal)
        self.style.right.alignment = TA_RIGHT

        self.style.indented = copy.deepcopy(self.style.normal)
        self.style.indented.leftIndent = 0.5 * cm

        self.style.tablenotes = copy.deepcopy(self.style.indented)
        self.style.tablenotes.fontName = "%s-Italic" % self.style.fontName

        self.style.paragraph = copy.deepcopy(self.style.normal)
        self.style.paragraph.spaceBefore = 1
        self.style.paragraph.spaceAfter = 1

        self.style.bullet = copy.deepcopy(self.style.normal)
        self.style.bullet.bulletFontName = "Symbol"
        self.style.bullet.bulletFontSize = 7
        self.style.bullet.bulletIndent = 6
        self.style.bullet.firstLineIndent = 0
        self.style.bullet.leftIndent = 15

        self.style.numberbullet = copy.deepcopy(self.style.normal)
        self.style.numberbullet.bulletFontName = self.style.paragraph.fontName
        self.style.numberbullet.bulletFontSize = self.style.paragraph.fontSize
        self.style.numberbullet.bulletIndent = 0
        self.style.numberbullet.firstLineIndent = 0
        self.style.numberbullet.leftIndent = 15

        # alignment = TA_RIGHT
        # leftIndent = 0.4*cm
        # spaceBefore = 0
        # spaceAfter = 0

        self.style.tableBase = (
            ("FONT", (0, 0), (-1, -1), "%s" % self.style.fontName, self.style.fontSize),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("FIRSTLINEINDENT", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        )

        self.style.table = self.style.tableBase + (
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        )

        self.style.tableLLR = self.style.tableBase + (
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        )

        self.style.tableHead = self.style.tableBase + (
            (
                "FONT",
                (0, 0),
                (-1, 0),
                "%s-Bold" % self.style.fontName,
                self.style.fontSize,
            ),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LINEABOVE", (0, 0), (-1, 0), 0.2, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), 0.2, colors.black),
        )

        self.style.tableOptional = self.style.tableBase + (
            (
                "FONT",
                (0, 0),
                (-1, 0),
                "%s-Italic" % self.style.fontName,
                self.style.fontSize,
            ),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (1, 0), (-1, -1), 2 * cm),
        )

    def init_templates(self, page_fn, page_fn_later=None):
        self.doc.addPageTemplates(
            [
                PageTemplate(id="First", frames=[self.frame], onPage=page_fn),
                PageTemplate(
                    id="Later", frames=[self.frame], onPage=page_fn_later or page_fn
                ),
            ]
        )
        self.story.append(NextPageTemplate("Later"))

    def init_report(self, page_fn=dummy_stationery, page_fn_later=None):
        frame_kwargs = {
            "showBoundary": self.show_boundaries,
            "leftPadding": 0,
            "rightPadding": 0,
            "topPadding": 0,
            "bottomPadding": 0,
        }

        full_frame = Frame(2.6 * cm, 2 * cm, 16.4 * cm, 25 * cm, **frame_kwargs)

        self.doc.addPageTemplates(
            [
                PageTemplate(id="First", frames=[full_frame], onPage=page_fn),
                PageTemplate(
                    id="Later", frames=[full_frame], onPage=page_fn_later or page_fn
                ),
            ]
        )
        self.story.append(NextPageTemplate("Later"))

        self.generate_style()

    def init_confidential_report(self, page_fn=dummy_stationery, page_fn_later=None):
        if not page_fn_later:
            page_fn_later = page_fn

        def _first_page_fn(canvas, doc):
            page_fn(canvas, doc)
            doc.PDFDocument.confidential(canvas)
            doc.PDFDocument.watermark("CONFIDENTIAL")

        self.init_report(page_fn=_first_page_fn, page_fn_later=page_fn_later)

    def init_letter(
        self,
        page_fn=dummy_stationery,
        page_fn_later=None,
        address_y=None,
        address_x=None,
    ):
        frame_kwargs = {
            "showBoundary": self.show_boundaries,
            "leftPadding": 0,
            "rightPadding": 0,
            "topPadding": 0,
            "bottomPadding": 0,
        }

        address_frame = Frame(
            address_x or 2.6 * cm,
            address_y or 20.2 * cm,
            16.4 * cm,
            4 * cm,
            **frame_kwargs
        )
        rest_frame = Frame(2.6 * cm, 2 * cm, 16.4 * cm, 18.2 * cm, **frame_kwargs)
        full_frame = Frame(2.6 * cm, 2 * cm, 16.4 * cm, 25 * cm, **frame_kwargs)

        self.doc.addPageTemplates(
            [
                PageTemplate(
                    id="First", frames=[address_frame, rest_frame], onPage=page_fn
                ),
                PageTemplate(
                    id="Later", frames=[full_frame], onPage=page_fn_later or page_fn
                ),
            ]
        )
        self.story.append(NextPageTemplate("Later"))

        self.generate_style()

    def watermark(self, watermark=None):
        self._watermark = watermark

    def restart(self):
        self.story.append(NextPageTemplate("First"))
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

    def ul(self, items):
        for item in items:
            self.story.append(MarkupParagraph(item, self.style.bullet, bulletText=u"•"))

    def spacer(self, height=0.6 * cm):
        self.story.append(Spacer(1, height))

    def table(self, data, columns, style=None):
        self.story.append(Table(data, columns, style=style or self.style.table))

    def hr(self):
        self.story.append(HRFlowable(width="100%", thickness=0.2, color=colors.black))

    def hr_mini(self):
        self.story.append(HRFlowable(width="100%", thickness=0.2, color=colors.grey))

    def mini_html(self, html):
        """Convert a small subset of HTML into ReportLab paragraphs

        Requires lxml and BeautifulSoup."""
        import lxml.html
        import lxml.html.soupparser

        TAG_MAP = {
            "strong": "b",
            "em": "i",
            "br": "br",  # Leave br tags alone
        }

        BULLETPOINT = u"•"

        def _p(text, list_bullet_point, style=None):
            if list_bullet_point:
                self.story.append(
                    MarkupParagraph(
                        text,
                        style or self.style.paragraph,
                        bulletText=list_bullet_point,
                    )
                )
            else:
                self.story.append(MarkupParagraph(text, style or self.style.paragraph))

        def _remove_attributes(element):
            for key in element.attrib:
                del element.attrib[key]

        def _handle_element(element, list_bullet_point=False, style=None):
            _remove_attributes(element)

            if element.tag in TAG_MAP:
                element.tag = TAG_MAP[element.tag]

            if element.tag in ("ul",):
                for item in element:
                    _handle_element(
                        item, list_bullet_point=BULLETPOINT, style=self.style.bullet
                    )
                list_bullet_point = False
            elif element.tag in ("ol",):
                for counter, item in enumerate(element):
                    _handle_element(
                        item,
                        list_bullet_point=u"{}.".format(counter + 1),
                        style=self.style.numberbullet,
                    )
                list_bullet_point = False
            elif element.tag in ("p", "li"):
                for tag in reversed(list(element.iterdescendants())):
                    _remove_attributes(tag)
                    if tag.tag in TAG_MAP:
                        tag.tag = TAG_MAP[tag.tag]
                    else:
                        tag.drop_tag()

                _p(
                    lxml.html.tostring(element, method="xml", encoding=string_type),
                    list_bullet_point,
                    style,
                )
            else:
                if element.text:
                    _p(element.text, list_bullet_point, style)

                for item in element:
                    _handle_element(item, list_bullet_point, style)

            if element.tail:
                _p(element.tail, list_bullet_point, style)

        soup = lxml.html.soupparser.fromstring(html)
        _handle_element(soup)

    def pagebreak(self):
        self.story.append(PageBreak())

    def bottom_table(self, data, columns, style=None):
        obj = BottomSpacer(1, 1)
        obj._doc = self.doc
        self.story.append(obj)

        self.story.append(BottomTable(data, columns, style=style or self.style.table))

    def append(self, data):
        self.story.append(data)

    def generate(self):
        self.doc.multiBuild(self.story)

    def confidential(self, canvas):
        canvas.saveState()

        canvas.translate(18.5 * cm, 27.4 * cm)

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

    def draw_watermark(self, canvas):
        if self._watermark:
            canvas.saveState()
            canvas.rotate(60)
            canvas.setFillColorRGB(0.9, 0.9, 0.9)
            canvas.setFont("%s" % self.style.fontName, 120)
            canvas.drawCentredString(195 * mm, -30 * mm, self._watermark)
            canvas.restoreState()

    def draw_svg(self, canvas, path, xpos=0, ypos=0, xsize=None, ysize=None):
        from reportlab.graphics import renderPDF
        from svglib.svglib import svg2rlg

        drawing = svg2rlg(path)
        xL, yL, xH, yH = drawing.getBounds()

        if xsize:
            drawing.renderScale = xsize / (xH - xL)
        if ysize:
            drawing.renderScale = ysize / (yH - yL)

        renderPDF.draw(drawing, canvas, xpos, ypos, showBoundary=self.show_boundaries)

    def next_frame(self):
        self.story.append(CondPageBreak(20 * cm))

    def start_keeptogether(self):
        self.keeptogether_index = len(self.story)

    def end_keeptogether(self):
        keeptogether = KeepTogether(self.story[self.keeptogether_index :])
        self.story = self.story[: self.keeptogether_index]
        self.story.append(keeptogether)

    def address_head(self, text):
        self.smaller(text)
        self.spacer(2 * mm)

    def address(self, obj, prefix=""):
        if type(obj) == dict:
            data = obj
        else:
            data = {}
            for field in (
                "company",
                "manner_of_address",
                "first_name",
                "last_name",
                "address",
                "zip_code",
                "city",
                "full_override",
            ):
                attribute = "%s%s" % (prefix, field)
                data[field] = getattr(obj, attribute, u"").strip()

        address = []
        if data.get("company", False):
            address.append(data["company"])

        title = data.get("manner_of_address", "")
        if title:
            title += u" "

        if data.get("first_name", False):
            address.append(
                u"%s%s %s"
                % (title, data.get("first_name", ""), data.get("last_name", ""))
            )
        else:
            address.append(u"%s%s" % (title, data.get("last_name", "")))

        address.append(data.get("address"))
        address.append(u"%s %s" % (data.get("zip_code", ""), data.get("city", "")))

        if data.get("full_override"):
            address = [
                l.strip()
                for l in data.get("full_override").replace("\r", "").splitlines()
            ]

        self.p("\n".join(address))

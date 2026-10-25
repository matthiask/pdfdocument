===========
PDFDocument
===========

This is a wrapper for ReportLab which allows easy creation of PDF documents::

    from io import BytesIO
    from pdfdocument.document import PDFDocument

    def say_hello():
        f = BytesIO()
        pdf = PDFDocument(f)
        pdf.init_report()
        pdf.h1('Hello World')
        pdf.p('Creating PDFs made easy.')
        pdf.generate()
        return f.getvalue()


Letters and reports
===================

PDFDocument comes with two different PDF templates, letters and reports. The
only difference is the layout of the first page: The letter has an additional
frame for the address at the top and a smaller main content area.

Usage is as follows::

    pdf.init_report()
    # Or:
    pdf.init_letter()

The letter generates default styles using 9 point fonts as base size, the report
uses 8 points. This can be changed by calling ``pdf.generate_style`` again.

There exists also a special type of report, the confidential report, the only
differences being that the confidentiality is marked using a red cross at the
top of the first page and a watermark in the background.


Styles
======

The call to ``pdf.generate_style`` generates a set of predefined styles. (Yes
it does!) That includes the following styles; this list is neither exhaustive
nor a promise:

- ``pdf.style.normal``
- ``pdf.style.heading1``
- ``pdf.style.heading2``
- ``pdf.style.heading3``
- ``pdf.style.small``
- ``pdf.style.bold``
- ``pdf.style.right``
- ``pdf.style.indented``
- ``pdf.style.paragraph``
- ``pdf.style.table``

Most of the time you will not use those attributes directly, except in the case
of tables. Convenience methods exist for almost all styles as described in the
next chapter.


Content
=======

All content passed to the following methods is escaped by default. ReportLab
supports a HTML-like markup language, if you want to use it directly you'll
have to either use only ``pdf.p_markup`` or resort to creating
``pdfdocument.document.MarkupParagraph`` instances by hand.


Headings
--------

``pdf.h1``, ``pdf.h2``, ``pdf.h3``


Paragraphs
----------

``pdf.p``, ``pdf.p_markup``, ``pdf.small``, ``pdf.smaller``


Unordered lists
---------------

``pdf.ul``

Mini-HTML
---------

``pdf.mini_html``


Various elements
----------------

``pdf.hr``, ``pdf.hr_mini``, ``pdf.spacer``, ``pdf.pagebreak``,
``pdf.start_keeptogether``, ``pdf.end_keeptogether``, ``pdf.next_frame``,


Tables
------

``pdf.table``, ``pdf.bottom_table``


Canvas methods
--------------

Canvas methods work with the canvas directly, and not with Platypus objects.
They are mostly useful inside stationery functions. You'll mostly use
ReportLab's canvas methods directly, and only resort to the following methods
for special cases.

``pdf.confidential``, ``pdf.draw_watermark``, ``pdf.draw_svg``


Additional methods
------------------

``pdf.append``, ``pdf.restart``


Django integration
==================

PDFDocument has a few helpers for generating PDFs in Django views, most notably
``pdfdocument.utils.pdf_response``::

    from pdfdocument.utils import pdf_response

    def pdf_view(request):
        pdf, response = pdf_response('filename_without_extension')
        # ... more code

        pdf.generate()
        return response

There are no templates involved -- you build the document in Python using the
methods described above, so "passing context" simply means using your data
directly::

    from django.shortcuts import get_object_or_404
    from reportlab.lib.units import cm
    from pdfdocument.utils import pdf_response

    def invoice_pdf(request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        pdf, response = pdf_response('invoice-%s' % invoice.pk)
        pdf.init_letter()
        pdf.address(invoice.customer)
        pdf.next_frame()
        pdf.h1('Invoice %s' % invoice.pk)
        pdf.table(
            [(item.title, '%.2f' % item.amount) for item in invoice.items.all()],
            (13 * cm, 3.4 * cm),
        )
        pdf.generate()
        return response

Pass ``as_attachment=False`` to ``pdf_response`` if the PDF should be shown
inline in the browser instead of being downloaded.


Examples
========

A letter with a custom stationery
---------------------------------

Stationery functions are called for every page with the ReportLab canvas and
the document template. They are the place to draw logos, footers and page
numbers. The first page and later pages may use different functions::

    from reportlab.lib.units import cm
    from pdfdocument.document import PDFDocument

    def stationery(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(2.6 * cm, 1 * cm, 'ACME Corp. · Main Street 1 · Springfield')
        canvas.drawRightString(19 * cm, 1 * cm, doc.page_index_string())
        canvas.restoreState()

    with open('letter.pdf', 'wb') as f:
        pdf = PDFDocument(f)
        pdf.init_letter(page_fn=stationery)
        pdf.address({
            'company': 'Example Inc.',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'address': 'Elm Street 5',
            'zip_code': '8000',
            'city': 'Zurich',
        })
        pdf.next_frame()  # Leave the address frame
        pdf.p('Dear Jane,')
        pdf.spacer()
        pdf.p('Thank you for your order.')
        pdf.generate()

``pdf.address`` accepts either a dictionary or an object with attributes of the
same name (optionally with a ``prefix``, e.g. ``prefix='billing_'``).

Tables
------

Tables take a list of rows and a list of column widths. The default table style
is available as ``pdf.style.table`` and can be extended with any `ReportLab
table style commands
<https://docs.reportlab.com/reportlab/userguide/ch7_tables/>`__::

    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    pdf.table(
        [('Item', 'Amount'), ('Consulting', '1200.00'), ('Hosting', '300.00')],
        (13 * cm, 3.4 * cm),
        TableStyle(pdf.style.tableHead + (
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        )),
    )

``pdf.bottom_table`` works the same way but pushes the table to the bottom of
the current frame, which is useful for signatures and totals.

Fonts
-----

Use ``register_fonts_from_paths`` to register a TrueType font family, then pass
the font name when instantiating the document::

    from pdfdocument.document import PDFDocument, register_fonts_from_paths

    register_fonts_from_paths(
        'fonts/Lato-Regular.ttf',
        'fonts/Lato-Italic.ttf',
        'fonts/Lato-Bold.ttf',
        'fonts/Lato-BoldItalic.ttf',
        font_name='Lato',
    )
    pdf = PDFDocument(f, font_name='Lato', font_size=10)

Mixing in arbitrary ReportLab flowables
---------------------------------------

Anything ReportLab can render as a flowable can be added using
``pdf.append``::

    from reportlab.platypus import Image

    pdf.append(Image('chart.png', width=10 * cm, height=6 * cm))


The SVG support uses svglib by Dinu Gherman. It can be found on PyPI:
<http://pypi.python.org/pypi/svglib/>

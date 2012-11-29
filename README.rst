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

``pdf.h1)``, ``pdf.h2``, ``pdf.h3``


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


The SVG support uses svglib by Dinu Gherman. It can be found on PyPI:
<http://pypi.python.org/pypi/svglib/>

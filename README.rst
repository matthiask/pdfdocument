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


Styles
======


Content
=======


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

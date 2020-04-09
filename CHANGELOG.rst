.. _changelog:

Change log
==========

`Next version`_
~~~~~~~~~~~~~~~


`v4.0`_ (2020-04-09)
~~~~~~~~~~~~~~~~~~~~

- Changed ``init_report`` and ``init_letter`` to not explicitly specify
  the font size of the document. This changes reports to use a default
  font size of ``9`` instead of ``8``.


`v3.3`_ (2019-03-04)
~~~~~~~~~~~~~~~~~~~~

- Fixed a grave bug where ``mini_html`` would silently drop content
  outside of HTML elements.


`v3.2`_ (2017-04-13)
~~~~~~~~~~~~~~~~~~~~

- Imported ``reduce`` from ``functools`` for Python 3 compatibility.


`v3.1`_ (2014-10-21)
~~~~~~~~~~~~~~~~~~~~

- Started building universal wheels.
- Added an option to ``init_letter`` to specify the X position of the
  address block.


`v3.0`_ (2014-01-03)
~~~~~~~~~~~~~~~~~~~~

- Added compatibility with Python 3.


.. _v3.0: https://github.com/matthiask/pdfdocument/commit/fe085bdf9
.. _v3.1: https://github.com/matthiask/pdfdocument/compare/v3.0...v3.1
.. _v3.2: https://github.com/matthiask/pdfdocument/compare/v3.1...v3.2
.. _v3.3: https://github.com/matthiask/pdfdocument/compare/v3.2...v3.3
.. _v4.0: https://github.com/matthiask/pdfdocument/compare/v3.3...v4.0
.. _Next version: https://github.com/matthiask/feincms3/compare/v4.0...master

#!/usr/bin/env python
import os
from distutils.core import setup

setup(
    name='pdfdocument',
    version='3.1',
    description='Programmatic wrapper around ReportLab.',
    long_description=open(
        os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    author='Matthias Kestenholz',
    author_email='mk@feinheit.ch',
    url='https://github.com/matthiask/pdfdocument/',
    packages=['pdfdocument'],
)

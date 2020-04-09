#!/usr/bin/env python3

import os
from io import open

from setuptools import find_packages, setup


def read(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, encoding="utf-8") as handle:
        return handle.read()


setup(
    name="pdfdocument",
    version=__import__("pdfdocument").__version__,
    description="Programmatic wrapper around ReportLab.",
    long_description=read("README.rst"),
    author="Matthias Kestenholz",
    author_email="mk@feinheit.ch",
    url="https://github.com/matthiask/pdfdocument/",
    packages=find_packages(exclude=["tests", "testapp"]),
    include_package_data=True,
    install_requires=["reportlab"],
)

# flake8: noqa
# type: ignore

import glob
import subprocess
import sys

import setuptools


try:
    from mypyc.build import mypycify
except ImportError:
    mypycify = None

from setuptools import Extension

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

build_with_mypyc = "--with-mypyc" in sys.argv
if build_with_mypyc:
    version = subprocess.check_output(['mypyc','--version'])
    print("mypyc:",version)
    sys.argv.remove("--with-mypyc")

if mypycify is not None and build_with_mypyc:
    files = glob.glob("soso/**/*.py",recursive=True)
    files = [f for f in files if f.find("__init__.py") == -1]
    ext_modules = mypycify(files)
else:
    ext_modules = []

setuptools.setup(
    name="soso-state",
    version="0.0.1",
    author="Sohail Somani",
    author_email="me@sohailsomani.com",
    description="Python 3.8+ application state container",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sohailsomani/soso-state",
    packages=['soso', 'soso.state'],
    namespace_packages=['soso'],
    package_data={
        'soso': ['*.pyi', 'py.typed'],
        'soso.state': ['*.pyi', 'py.typed']
    },
    ext_modules = ext_modules,
    classifiers=[
        "Programming Language :: Python :: 3.8", "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.8",
)

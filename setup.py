# flake8: noqa
# type: ignore

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="soso-state",
    version="0.0.1",
    author="Sohail Somani",
    author_email="me@sohailsomani.com",
    description="Python 3.8+ application state container",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sohailsomani/soso.state",
    install_requires=[
        "soso-event @ git+https://github.com/sohailsomani/soso-event.git#egg=soso-event"
    ],
    packages=['soso.state'],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.8",
)

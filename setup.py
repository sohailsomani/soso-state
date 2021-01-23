import setuptools

with open("README.md","r",encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "soso-statetree",
    version="0.0.1",
    author="Sohail Somani",
    author_email="me@sohailsomani.com",
    description="Python 3.9+ application state container",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url="https://github.com/sohailsomani/soso-statetree",
    packages = setuptools.find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.9"
)

from platform import python_version
from setuptools import setup

from pathlib import Path

HERE = Path(__file__).parent
long_description = (HERE / "README.md").read_text()

requirements = [
    "pytesseract",
    "spacy",
    "ipycanvas",
    "ipycytoscape",
    "ipyevents",
    "ipywidgets",
    "traitlets",
    "numpy <=1.19.2,>=1.13",
    "pillow <=9.0.0",
    "pdf2image",
    "protobuf <=3.20",
    "layoutparser[paddledetection]",
]

setup(
    name="ipypdf",
    version="0.1.8",
    description="Jupyter widget for applying nlp to pdf documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Joel Stansbury",
    author_email="stansbury.joel@gmail.com",
    url="https://github.com/JoelStansbury/ipypdf",
    packages=["ipypdf"],
    package_data={
        "ipypdf": ["utils/*", "widgets/*", "style/*", "notebooks/*"],
    },
    install_requires=requirements,
    keywords="ipypdf",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)

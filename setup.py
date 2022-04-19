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
    "ipytree",
    "traitlets",
    "numpy <=1.19.3,>=1.13",
    "pdf2image",
    "layoutparser",
    "layoutparser[paddledetection]",
    "matplotlib",
]

setup(
    name="ipypdf",
    version="0.1.2",
    description="Jupyter widget for applying nlp to pdf documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Joel Stansbury",
    author_email="stansbury.joel@gmail.com",
    url="https://github.com/JoelStansbury/ipypdf",
    packages=["ipypdf", "tests"],
    package_data={
        "ipypdf": ["utils/*", "widgets/*", "style/*"],
        "tests": [
            ".py",
            "fixture_data/*.pdf",
            "fixture_data/*.json",
        ],
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

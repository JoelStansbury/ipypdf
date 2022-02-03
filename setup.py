from setuptools import setup

from pathlib import Path
HERE = Path(__file__).parent
long_description = (HERE / "README.md").read_text()

requirements = [
    "pytesseract",
    "spacy",
    "jupyterlab",
    "ipycanvas",
    "ipycytoscape",
    "ipyevents",
    "ipywidgets",
    "ipytree",
    "traitlets",
    "pdf2image",
    "layoutparser",
    "layoutparser[paddledetection]",
    "opencv-python",
    "numpy",
    "pandas",
    "matplotlib",
]

setup(
    name='ipypdf',
    version="0.0.3",
    description="Jupyter widget for applying nlp to pdf documents",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="MIT",
    author="Joel Stansbury",
    author_email='stansbury.joel@gmail.com',
    url='https://github.com/JoelStansbury/ipypdf',
    packages=['ipypdf'],
    package_data = {'ipypdf': [
        'utils/*',
        'widgets/*',
        'style/*'
    ]},
    install_requires=requirements,
    keywords='ipypdf',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)

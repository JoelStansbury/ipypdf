from setuptools import setup

import versioneer

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
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Jupyter widget for applying nlp to pdf documents",
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
    entry_points={
        'console_scripts': [
            'ipypdf=ipypdf.cli:cli'
        ]
    },
    install_requires=requirements,
    keywords='ipypdf',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)

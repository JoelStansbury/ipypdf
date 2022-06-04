# ipypdf

Jupyter widget for applying nlp to pdf documents


## Development
Useful info for Development
### Installation
```bash
conda env create -f environment.yml -p envs/ipypdf
conda activate envs/ipypdf
pip install -e . --no-dependencies
```
### Dev Utilities
These helper commands are stored in `anaconda-project.yml`. Normally, the environment
is defined in this file, but environment variables are not always handled correctly.
This causes problems with Tesseract, so I've opted to define the environment in
a more static manner.

* Build the conda package<br>
    `conda build ipypdf -c conda-forge --output-folder="build/"`

* PyPi packaging
    ```bash
    python -m pip install --upgrade build
    python -m pip install --upgrade twine
    python -m build
    python -m twine upload --repository pypi dist/*
    ```

* Test
    `pytest --cov=ipypdf tests/`

* Formatting
    * `isort ipypdf/ tests/`
    * `black ipypdf/ tests/ -l 79`
    * `flake8 ipypdf/ tests/ --ignore W503`
    * `pylint ipypdf/ tests/ --rcfile=.pylintrc`
    
* Updating Windows Installer
```bash
conda install constructor
conda install nsis
cd installer
constructor .
```
Upload the new executable to the google drive. Also, come up with a better place to put these


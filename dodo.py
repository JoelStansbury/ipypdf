from subprocess import check_output, call
import os
import platform
import sys

# Tasks to run during `doit` (with no args)
DOIT_CONFIG = {'default_tasks': ['update_deps', 'install_ipypdf']}


# Use mamba by default
USE_MAMBA = True

# Automatically agree to conda actions
os.environ["CONDA_ALWAYS_YES"] = "true"

# Location of environment file
ENV_FILE = "environment.yml"

# Path to environment
ENV_PATH = "./.venv"

PYPI_USERNAME = "JoelStansbury"
PYPI_PASSWORD = ""
with open("../keys/pypi", "r") as f:
    PYPI_PASSWORD = f.read()

PLATFORM = platform.system()
PYTHON = sys.executable

class CONDA:
    _conda = "mamba" if USE_MAMBA else "conda"
    update = f'{_conda} env update -f "{ENV_FILE}" -p "{ENV_PATH}"'
    activate = f'{_conda} activate "{ENV_PATH}"'

class PyPi:
    update_build_deps = "python -m pip install --upgrade build twine"
    build_ipypdf = "python -m build"
    upload = f"python -m twine upload --repository pypi dist/* -u {PYPI_USERNAME} -p {PYPI_PASSWORD}"
    distribute = f"{update_build_deps} && {build_ipypdf} && {upload}"

# Formatting
sort_imports = "isort ipypdf/ tests/"
black_format = "black ipypdf/ tests/ -l 79"
CLEAN = f"{CONDA.activate} && {sort_imports} && {black_format}"

def task_update_deps():
    return {
        "actions": [
            CONDA.update
        ],
        "file_dep": [ENV_FILE],
    }

def task_install_ipypdf():
    return {
        "actions": [
            f"{CONDA.activate} && pip install -e ."
        ]
    }

def task_launch():
    return {
        "actions": [
            f"{CONDA.activate} && jupyter lab ipypdf/notebooks/iPyPDF.ipynb"
        ]
    }

def task_test():
    return {
        "actions": [
            f"{CONDA.activate} && {CLEAN} && pytest"
        ],
        "verbosity": 2,
    }

def task_publish():
    return {
        "actions": [
            f"{CONDA.activate} && {CLEAN} && pytest && {PyPi.distribute}"
        ],
        "verbosity": 2,
    }
    
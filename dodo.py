from subprocess import check_output, call
import os
import platform
import sys

# Use mamba by default
USE_MAMBA = True

# Automatically agree to conda actions
os.environ["CONDA_ALWAYS_YES"] = "true"

# Location of environment file
ENV_FILE = "environment.yml"

# Path to environment
ENV_PATH = "./.venv"

# Tasks to run during `doit` (with no args)
DOIT_CONFIG = {'default_tasks': ['update_deps', 'install_ipypdf']}


PLATFORM = platform.system()
PYTHON = sys.executable

class CONDA:
    _conda = "mamba" if USE_MAMBA else "conda"
    update = f'{_conda} env update -f "{ENV_FILE}" -p "{ENV_PATH}"'
    activate = f'{_conda} activate "{ENV_PATH}"'

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
            f"{CONDA.activate} && pytest"
        ],
        "verbosity": 2,
    }

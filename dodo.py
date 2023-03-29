import os
import platform
import sys
from pathlib import Path

Path("logs").mkdir(exist_ok=True)
# Tasks to run during `doit` (with no args)
DOIT_CONFIG = {
    'default_tasks': ['setup'],
    'dep_file': 'logs/doit-db.json',
}


# Use mamba by default
USE_MAMBA = True

# Automatically agree to conda actions
os.environ["CONDA_ALWAYS_YES"] = "true"

# Location of environment file
ENV_FILE = "environment.yml"

# Path to environment
ENV_PATH = "./.venv"

PLATFORM = platform.system()
PYTHON = sys.executable

class CONDA:
    specs = []
    @classmethod
    def prepare(cls, spec):
        yield {
            "name": f"prepare ({spec})",
            "actions": [f"mamba env update -p .envs/{spec} -f deploy/specs/{spec}.yml"],
            "file_dep": [f"deploy/specs/{spec}.yml"],
        }

    @classmethod
    def run_in(cls, spec, tasks):
        yield cls.prepare(spec)
        for task in tasks:
            yield dict(
                actions=[f"conda run --no-capture-output --live-stream -p .envs/{spec} {action}" for action in task.pop('actions')],
                **task
            )


def task_setup():
    return CONDA.run_in(
        spec="dev",
        tasks=[
            dict(
                name="install layoutparser",
                actions=['python -m pip install layoutparser==0.3.4 --no-deps'],
                verbosity=2,
            ),
            dict(
                name="install paddlepaddle",
                actions=['python -m pip install paddlepaddle==2.1.0 --no-deps'],
                verbosity=2,
            ),
            dict(
                name="install src",
                actions=['python -m pip install -e . --no-deps'],
                verbosity=2,
            ),
            dict(
                name="pip check",
                actions=['python -m pip check'],
                verbosity=2,
            ),
        ]
    )

def task_test():
    return CONDA.run_in(
        spec="dev",
        tasks=[
            dict(
                name="run pytests",
                actions=['pytest'],
                verbosity=2,
            ),
        ]
    )

def task_launch():
    return CONDA.run_in(
        spec="dev",
        tasks=[
            dict(
                name="launch",
                actions=['jupyter lab']
            ),
        ]
    )

def task_lint():
    return CONDA.run_in(
        spec="qa",
        tasks=[
            dict(
                name="launch",
                actions=[
                    "isort ipypdf/ tests/", 
                    "black ipypdf/ tests/ -l 79"
                ]
            ),
        ]
    )


def task_deploy():
    (Path(__file__).parent /"deploy/locks").mkdir(exist_ok=True)
    return CONDA.run_in(
        spec="build",
        tasks=[
            dict(
                name="package layoutparser",
                actions=["conda mambabuild recipes/layoutparser"],
                file_dep=["recipes/layoutparser/meta.yaml", "recipes/layoutparser/bld.bat"],
            ),
            dict(
                name="package wand",
                actions=["conda mambabuild recipes/wand"],
                file_dep=["recipes/wand/meta.yaml"],
            ),
            dict(
                name="package ipypdf",
                actions=["conda mambabuild recipes/ipypdf"],
            ),
            dict(
                name="build",
                actions=["widgetron ."],
                verbosity=2,
            ),
        ]
    )
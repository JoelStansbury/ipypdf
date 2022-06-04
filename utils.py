import subprocess
from pathlib import Path
import os
import sys

ROOT = Path(__file__).parent.resolve()
ENV = os.environ["CONDA_PREFIX"]
ENV_PATH = ROOT / "env" / "ipypdf"
ENV_FILE = ROOT / "environment.yml"
DIST = ROOT / "dist"
PYTHON = sys.executable

ENV_ACTIVE = ENV == str(ENV_PATH)
ENV_EXISTS = ENV_PATH.exists()


def setup_environment():
    subprocess.call(["mamba", "env", "create", "-f", ENV_FILE, "-p", ENV_PATH])
    print("Environment Created. Activate it now with ...\n\tconda activate env/ipypdf")

# Doesn't work
# def update_environment():
#     if not ENV_ACTIVE:
#         print(f"\nPlease activate the environment...\n\tconda activate {ENV_PATH}")
#     subprocess.call(["mamba", "env", "update", "-f", ENV_FILE])

def build():
    subprocess.check_call([PYTHON, "-m", "build", "--outdir", DIST])

if __name__ == "__main__":
    if not ENV_EXISTS:
        setup_environment()
        exit()
    if not ENV_ACTIVE:
        print(f"Please activate the environment...\n\tconda activate {ENV_PATH}")
        exit()
    build()
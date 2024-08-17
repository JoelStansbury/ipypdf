import os
import shutil
import sys
from pathlib import Path

tessdata = Path(os.environ["TESSDATA_PREFIX"]) / "configs"
tessconfig = Path(sys.prefix) / "Library/share/tessdata/configs"
if not tessdata.exists():
    shutil.copytree(src=tessconfig, dst=tessdata) 
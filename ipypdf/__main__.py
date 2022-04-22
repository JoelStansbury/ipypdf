import sys
import menuinst
import os
from pathlib import Path

HERE = Path(__file__).parent
ENV = Path(sys.executable).parent

if __name__ == "__main__":
    args = sys.argv
    if args and args[1] == "make_shortcut":
        # NOTE: doesn't work on editable install
        menuinst.install(str(HERE / "menu.json"))
    if args and args[1] == "remove_shortcut":
        menuinst.install(str(HERE / "menu.json"), remove=True)
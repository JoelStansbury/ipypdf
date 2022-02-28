from pathlib import Path
import os
HERE = Path(__file__).parent
ROOT = HERE.parent
ENV = ROOT / "envs/developer"

guess = ENV / "share/tessdata"
if guess.exists():
    tess_data = str(guess.resolve())
    os.environ["TESSDATA_PREFIX"] = tess_data

else:
    for folder in ENV.rglob("tessdata"):
        if (folder / 'eng.traineddata').exists():
            os.environ["TESSDATA_PREFIX"] = str(folder.resolve())
            break

print(os.environ["TESSDATA_PREFIX"])
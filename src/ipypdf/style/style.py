from pathlib import Path

from ipywidgets import HTML

HERE = Path(__file__).parent
with open(HERE / "style.css", "r") as f:
    CSS = HTML(f"<style>\n{f.read()}\n</style>")

from ._version import get_versions
from .app import App

__version__ = get_versions()["version"]
# print(get_versions()["error"])
del get_versions

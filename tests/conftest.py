# The conftest.py file serves as a means of providing
# fixtures for an entire directory.
# Fixtures defined in a conftest.py can be used by any
# test in that package without needing to import them
# (pytest will automatically discover them).
# https://docs.pytest.org/en/latest/reference/fixtures.html
#       #conftest-py-sharing-fixtures-across-multiple-files
from pathlib import Path

import pytest

import ipypdf

HERE = Path(__file__).parent
DOC_DIR = HERE / "fixture_data"


@pytest.fixture()
def app():
    return ipypdf.App(DOC_DIR)


@pytest.fixture()
def root_node(app):
    return app.tree_visualizer.root


@pytest.fixture()
def pdf_nodes(root_node):
    return [x for x in root_node.dfs() if x._type == "pdf"]

from collections import defaultdict
from ipypdf.widgets.node_tools import AutoTools


def test_install_layoutparser(root_node):
    """
    layoutparser is not available on conda-forge.
    The workaround is to provide a button (visible to the user)
    which provides the option to install layoutparser and
    the corresponding paddlepaddle model for parsing.
    """
    util = AutoTools(root_node)
    if util.layoutparser_btn.description == "Install":
        util.install_layoutparser()
        assert (
            util.layoutparser_btn.description == "Parse Layout"
        ), "Install layoutparser Failed"


def test_parse_layout(pdf_nodes):
    """
    Check that the layout model runs and adds content properly
    """
    doc_node = pdf_nodes[0]
    doc_node.nodes = []  # clear any previously defined nodes

    AutoTools(doc_node).extract_layout()
    assert len(doc_node.nodes) > 0, "Layoutparser could not find any nodes"

    types = defaultdict(list)
    for x in doc_node.dfs():
        types[x._type].append(x.label)

    assert len(types["section"]) == 3, types["section"]
    assert len(types["image"]) == 1, f"Did not find image {types.keys()}"
    assert len(types["table"]) == 1, f"Did not find table {types.keys()}"
    assert len(types["text"]) == 6
from ipypdf.widgets.node_tools import AutoTools


def test_parse_text(pdf_nodes):
    """
    Check that the ocr model runs and adds content properly
    """
    doc_node = pdf_nodes[0]
    doc_node.nodes = []  # clear any previously defined nodes

    AutoTools(doc_node).extract_text()
    assert len(doc_node.nodes) > 0, "Layoutparser could not find any nodes"

    # Cleanup
    doc_node.nodes = []

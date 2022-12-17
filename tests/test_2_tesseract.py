from ipypdf.widgets.node_tools import AutoTools


def test_parse_text(app, pdf_nodes):
    """
    Check that the ocr model runs and adds content properly
    """
    doc_node = pdf_nodes[0]
    app.tree.remove_children(doc_node)  # clear any previously defined nodes

    AutoTools(doc_node).extract_text()
    assert (
        len(doc_node.data["children"]) > 0
    ), "Layoutparser could not find any nodes"

    # Cleanup
    app.tree.remove_children(doc_node)

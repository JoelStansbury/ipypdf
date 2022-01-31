def test_pdfs_detected(app, root_node):
    """
    Check that the app properly detects the pdf files located in
    fixtures/sample_docs.
    """
    pdfs = [x.label for x in root_node.dfs() if x._type == "pdf"]
    assert "doc.pdf" in pdfs

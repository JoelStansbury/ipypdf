def test_pdfs_detected(app):
    """
    Check that the app properly detects the pdf files located in
    fixtures/sample_docs.
    """
    pdfs = [x.data['label'] for x in app.tree.dfs() if x.data['type'] == "pdf"]
    assert "doc.pdf" in pdfs

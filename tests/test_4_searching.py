from ipypdf.widgets.node_tools import Search


def test_search(root_node):
    tool = Search(root_node)
    assert len(tool.results) == 0
    tool.search(query="Disclaimer", case_sensitive=False)
    assert len(tool.results) > 0, "No results found"

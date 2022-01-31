from ipypdf.widgets.node_tools import SubsectionTools
from ipypdf.utils.image_utils import rel_2_canvas


def test_select_nodes(app, root_node):
    types = ["folder", "pdf", "section", "image", "table", "text"]

    for t in types:
        node = [x for x in root_node.dfs() if x._type == t][0]
        app.tree_visualizer.set_trait("selected_nodes", (node,))


def test_draw_textbox(app, root_node):
    """
    Simulate manual text block selection. I.e., clicking on the button
    to make a new text node. Then clicking on the rendered image to start
    the bbox. Drag the mouse to complete the bbox. Release mouse to process
    the contents.
    """
    node = [x for x in root_node.dfs() if x._type == "pdf"][0]
    app.tree_visualizer.set_trait("selected_nodes", (node,))

    # append a text node by clicking the button to do so
    SubsectionTools(node).text.click()

    # select the node because the events don't happen in tests
    node = node.nodes[-1]
    app.tree_visualizer.set_trait("selected_nodes", (node,))

    # verify that a text node was made
    assert node._type == "text"
    assert len(node.content) == 0

    w = app.full_img.width * app.scaling_factor
    h = app.full_img.height * app.scaling_factor
    coords = [
        0.11490196078431372,
        0.8772549019607843,
        0.6485913359588004,
        0.7161466222356861,
    ]
    # relative coordinates of a text block in the fixture pdf

    x1, y1, x2, y2 = rel_2_canvas(coords, w, h)

    # simulate the mouse events to set the canvas.rect
    app.canvas.mouse_down(x1, y1)
    app.canvas.mouse_move(x2, y2)
    app.canvas.mouse_up(x2, y2)

    # Usually this is handled by the mouseup event, but that doesn't
    # happen here because there is no actual mouseup_event
    app.parse_current_selection(x2, y2)
    assert node.content[0]["value"].strip().startswith("Lorem")

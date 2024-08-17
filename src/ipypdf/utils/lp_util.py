
import warnings

# This library prints out a bunch of model info as a warning and it looks bad
with warnings.catch_warnings():
    print("lp utils")
    warnings.simplefilter("ignore")
    import deepdoctection as dd

from .image_utils import pil_2_rel

CHILD = dd.Relationships.CHILD
TYPE_MAP = {
    dd.LayoutType.TITLE: "Title",
    dd.LayoutType.TEXT: "Text",
    dd.LayoutType.TABLE: "Table",
    dd.LayoutType.FIGURE: "Figure",
    dd.LayoutType.LIST: "List",
}


def sort_layout(layout: list):
    x_min = float("inf")
    x_max = 0
    for block in layout:
        mn = block.bbox[0]
        mx = block.bbox[2]
        x_min = mn if mn < x_min else x_min
        x_max = mx if mx > x_max else x_max
    page_width = x_max - x_min

    def column(pil_coords):
        # NOTE: This places an upper-bound on columns
        # TODO: Check for changes in the predicted number of columns
        # and fix multi-column blocks vertically so that they don't get pushed
        # to the end if it changes further down
        x1, _, x2, _ = pil_coords

        if abs(x1 - x_min) < (page_width / 3):  # Max of 3 columns
            return 0

        # if it is centered then column = 0
        w = x2 - x1
        mid = x1 + (w / 2)
        page_mid = x_min + (page_width / 2)
        if abs(page_mid - mid) < (page_width / 50):
            return 0

        # max possible number of columns
        # c_num = int(page_width//w)

        return (x1 - x_min) // (page_width / 10)

    layout.sort(key=lambda x: (column(x.bbox), x.bbox[1]))


def parse_layout(fname, model=None, start=0, stop=-1, ignore_warning=False):
    if model is None:
        model = (
            dd.get_dd_analyzer()
        )  # instantiate the built-in analyzer similar to the Hugging Face space demo

    df = model.analyze(path=fname)  # setting up pipeline
    df.reset_state()  # Trigger some initialization

    for page in iter(df):
        layout = list(page.layouts) + list(page.tables)
        for block in layout:
            block.relative_coordinates = pil_2_rel(
                block.bbox, page.width, page.height
            )
            block.type = TYPE_MAP[block.category_name]
            block.children = []

        sort_layout(layout)
        current_section = []
        for b in layout:
            if b.type == "Title":
                current_section = b.children
            else:
                current_section.append(b.annotation_id)
        yield layout

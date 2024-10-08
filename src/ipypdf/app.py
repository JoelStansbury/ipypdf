import json
import os
import sys
from pathlib import Path

import ipywidgets as ipyw

from .style.style import CSS
from .utils.image_utils import (
    ImageContainer,
    canvas_2_rel,
    fit,
    pil_2_widget,
    rel_2_canvas,
    rel_crop,
    scale,
)
from .utils.tree_utils import file_path, load_from_json, to_dict
from .widgets.better_tree import Tree, TreeWidget
from .widgets.canvas import PdfCanvas
from .widgets.navigation import NavigationToolbar
from .widgets.node_tools import NodeDetail

# TODO: test if this works on linux and mac
os.environ["TESSDATA_PREFIX"] = f"{sys.prefix}/share/tessdata"

import pytesseract as tess

DEFAULT_DIRECTORY = os.path.expanduser("~/Documents/iPyPDF")
Path(DEFAULT_DIRECTORY).mkdir(exist_ok=True)


class App(ipyw.HBox):
    def __init__(self, directory=DEFAULT_DIRECTORY, bulk_render=False):
        super().__init__()
        self.add_class("ipypdf-main-app")

        self.bulk_render = bulk_render
        self.fname = ""
        self.active_node = None
        self.active_node_id = None
        self.last_image = None
        self.full_img = None

        self.navigator = NavigationToolbar()
        self.canvas = PdfCanvas(height=1000)

        self.tree = Tree()
        self.tree.rglob(directory, "*.pdf")

        for p, node in list(self.tree.registry.items()):
            if Path(p).suffix.lower() == ".pdf":
                json_file = Path(p).with_suffix(".json")
                if json_file.exists():
                    load_from_json(json_file, parent=node)

        self.tree_visualizer = TreeWidget(self.tree, height=30)
        self.root = self.tree.root
        self.node_detail = NodeDetail(
            self.root,
            self.navigator,
        )

        self.tree_visualizer.observe(
            self.on_selection_change, "selected_id", type="change"
        )
        self.navigator.prev_page_button.on_click(self.prev_page)
        self.navigator.next_page_button.on_click(self.next_page)
        self.navigator.save_button.on_click(self.save)
        self.navigator.draw_bboxes.observe(self.redraw_boxes, "value")

        self.canvas.animated_layer.on_mouse_up(self.parse_current_selection)

        # Load the first file
        self.SELECTION_PIPES = {
            "text": self.handle_textblock,
            "image": self.handle_image,
            "table": self.handle_table,
            "section": self.handle_label,
        }

        tree_box = ipyw.VBox([self.tree_visualizer])

        self.children = [
            tree_box,
            self.canvas,
            ipyw.VBox(
                [
                    CSS,
                    self.navigator,
                    self.node_detail,
                ]
            ),
        ]

    def on_selection_change(self, event):
        """
        Render the pdf selected in `file_dd` and load in any JSON file which
        may have been previously generated for it.
        """
        # Selecting a new node causes two events, one for deselecting the old
        # one and another for selecting the new one. We are concerned with the
        # new node so we ignore the first event by asserting that new is not None.
        if event["new"]:
            node = self.tree_visualizer.selected_node

            self.active_node = node
            self.selection_pipe = self.SELECTION_PIPES.get(
                node.data["type"], None
            )
            fname = file_path(node)
            self.node_detail.set_node(node)

            if fname is not None and fname.suffix.lower() == ".pdf":
                if fname != self.fname:
                    self.imgs = ImageContainer(
                        fname, bulk_render=self.bulk_render
                    )
                    self.n_pages = self.imgs.info["Pages"]
                    self.fname = fname
                    self.img_index = 0
                if self.navigator.draw_bboxes.value:
                    if node.data.get("content", []):
                        self.img_index = node.data["content"][0]["page"]
                    if node.data["type"] == "pdf":
                        self.img_index = 0
                self.load()
            else:
                self.canvas.clear()
                self.canvas.bg_layer.clear()
                self.fname = fname
                self.last_image = None

    def redraw_boxes(self, _=None):
        self.canvas.clear()
        if self.navigator.draw_bboxes.value:
            bboxes = []
            for node in self.tree.dfs(self.active_node.id):
                _type = node.data["type"]
                for c in node.data.get("content", []):
                    if c["page"] == self.img_index:
                        bboxes.append(
                            (
                                rel_2_canvas(
                                    c["coords"],
                                    self.full_img.width * self.scaling_factor,
                                    self.full_img.height * self.scaling_factor,
                                ),
                                _type,
                            )
                        )
            self.canvas.draw_many(bboxes)
        self.canvas.set_type(self.active_node.data["type"])

    def next_page(self, _=None):
        if self.img_index < self.n_pages - 1:
            self.canvas.clear()
            self.img_index += 1
            self.load()

    def prev_page(self, _=None):
        if self.img_index > 0:
            self.canvas.clear()
            self.img_index -= 1
            self.load()

    def load(self):
        if (self.fname, self.img_index) != self.last_image:
            self.canvas.clear()
            self.full_img = self.imgs[self.img_index]
            self.scaling_factor = fit(
                self.full_img, self.canvas.width, self.canvas.height
            )

            img = scale(self.full_img, self.scaling_factor)
            self.canvas.add_image(pil_2_widget(img))
            self.last_image = (self.fname, self.img_index)
        self.redraw_boxes()

    def parse_current_selection(self, x, y):
        w = self.scaling_factor * self.full_img.width
        h = self.scaling_factor * self.full_img.height
        self.selection_pipe(canvas_2_rel(self.canvas.rect, w, h))
        self.node_detail.set_node(self.active_node)

    def handle_image(self, rel_coords):
        self.active_node.data["content"].append(
            {"value": None, "page": self.img_index, "coords": rel_coords}
        )

    def handle_table(self, rel_coords):
        self.active_node.data["content"].append(
            {"value": None, "page": self.img_index, "coords": rel_coords}
        )

    def handle_label(self, rel_coords):
        text = tess.image_to_string(rel_crop(self.full_img, rel_coords))

        selected_node = self.active_node
        selected_node.label = text.strip()

        # store the coords of the headding for training purposes
        item = {
            "value": text.strip(),
            "page": self.img_index,
            "coords": rel_coords,
        }
        selected_node.data["content"] = [item]
        selected_node.data["label"] = text.strip()
        self.tree_visualizer.refresh()
        self.redraw_boxes()

    def handle_textblock(self, rel_coords):
        text = tess.image_to_string(
            rel_crop(self.full_img, rel_coords),
            config="--psm 1",  # Automatic page segmentation with OSD.
        )

        item = {"value": text, "page": self.img_index, "coords": rel_coords}
        self.active_node.data["content"].append(item)

    def save(self, _=None):
        for id, node in self.tree.registry.items():
            if Path(id).exists() and Path(id).suffix.lower() == ".pdf":
                data = to_dict(node)
                if data:
                    with Path(id).with_suffix(".json").open(mode="w") as f:
                        json.dump(data, f)

import sys
from collections import defaultdict
from pathlib import Path

import deepdoctection as dd
import pandas as pd
import spacy
from ipycytoscape import CytoscapeWidget
from ipywidgets import (
    HTML,
    Button,
    Checkbox,
    FloatSlider,
    HBox,
    Tab,
    Text,
    Textarea,
    ToggleButton,
    VBox,
)

from ..utils.constants import NODE_COLORS
from ..utils.image_utils import ImageContainer, rel_2_pil
from ..utils.lp_util import parse_layout
from ..utils.nlp import tfidf_similarity
from ..utils.table_extraction import img_2_table
from ..utils.tess_utils import get_text_blocks
from ..utils.tree_utils import (
    file_path,
    immediate_children,
    natural_path,
    select,
    stringify,
)
from .dataframe_widget import DataFrame
from .helper_widgets import SmallButton, Warnings

NODE_KWARGS = {
    "folder": [0, 5, 8],
    "pdf": [6, 1, 5, 4, 8],
    "section": [1, 5, 4, 8],
    "text": [3, 4, 8],
    "image": [2],
    "table": [7],
}

LP_DESC = (
    "Layout Extraction will use deepdoctectron to find"
    + " and label images, tables, titles, and normal text within"
    + " the document. Then, the coordinates of each node are used"
    + ' to predict the "natural order" with which the nodes'
    + " would be read."
)

TESS_DESC = (
    'Text Extraction uses <a href="'
    + 'https://github.com/tesseract-ocr/tesseract" '
    + 'style="color:blue;">tesseract</a> to find'
    + " and label textblocks within the document. The order is typically"
    + " more accurate than that of LayoutExtraction. It also tends to "
    + "handle slide shows better than layout parser as it was trained "
    + "on a much more diverse dataset."
)

NAVIGATOR = None
PYTHON = sys.executable
PREFIX = Path(PYTHON).parent
MODELS = PREFIX / "etc/ipypdf_models"


class NodeDetail(Tab):
    def __init__(self, node, nav_hook):
        super().__init__(layout={"height": "900px"})
        global NAVIGATOR
        NAVIGATOR = nav_hook

        self.node = node
        self.tabs = [
            HTML("Select a section for inspection"),
            SubsectionTools(node),
            ImageTools(node),
            TextBlockTools(node),
            SpacyInsights(node),
            Cytoscape(node),
            AutoTools(node),
            TableTools(node),
            Search(node),
            # SectionInsights(node),
            # Summary(node),
        ]
        # self.children = self.tabs
        self._titles = [
            "Info",
            "Tools",
            "ImageTools",
            "TextTools",
            "Spacy",
            "Cytoscape",
            "AutoTools",
            "TableTools",
            "Search",
            # "Insights",
            # "Summary",
        ]

        self.titles = self._titles

    def set_node(self, node):
        self.node = node
        indexes = NODE_KWARGS[self.node.data["type"]]
        children = []
        titles = []
        for i in indexes:
            children.append(self.tabs[i])
            titles.append(self._titles[i])
            if getattr(self.tabs[i], "set_node", False):
                self.tabs[i].set_node(node)
        self.children = children
        self.titles = titles


class MyTab(HBox):
    def __init__(self):
        super().__init__()
        # TODO: when I made this init I thought this would only be run once,
        # that is not the case. Refactor this to only run once.
        self.delete_btn = SmallButton(
            "trash",
            "Delete this node and all of its children",
            self.delete_node,
            "ipypdf-red",
        )

    def add_node(self, btn):
        NAVIGATOR.draw_bboxes.value = False
        new_node = {
            "type": self._types[btn],
            "children": [],
            "content": [],
        }
        node = self.node.controller.insert(new_node, self.node.id)
        select(node, goto=False)

    def set_node(self, node):
        self.node = node

    def delete_node(self, _=None):
        tree = self.node.controller
        if self.node.data["type"] == "pdf":
            tree.remove_children(self.node)
        else:
            tree.remove(self.node)


class SubsectionTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.text = SmallButton(
            "align-left", "Add a new text node", self.add_node
        )
        section = SmallButton("indent", "Add a subsection", self.add_node)
        image = SmallButton("image", "Add an image", self.add_node)
        table = SmallButton("table", "Add a Table", self.add_node)

        self._types = {
            self.text: "text",
            section: "section",
            image: "image",
            table: "table",
        }

        self.children = [section, self.text, image, table, self.delete_btn]


class ImageTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        text = SmallButton(
            "align-left", "Add a description for the image", self.add_node
        )

        self._types = {
            text: "text",
        }

        self.children = [text, self.delete_btn]


class TextBlockTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

    def redraw_content(self, _=None):
        """
        Updates the tab to show updated content. Lists out each of
        the elements in self.node.data["content"] as a block of text
        to show the results of the OCR.
        TODO: These boxes are editable, but there's no procedure for
        propagating changes back to the node
        """
        self.children = [
            VBox([Textarea(x["value"]) for x in self.node.data["content"]]),
            self.delete_btn,
        ]

    def set_node(self, node):
        self.node = node
        self.redraw_content()


class SpacyInsights(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.info = Warnings()
        self.model_path = Text(
            placeholder="path/to/pipeline  (en_core_web_sm)",
            continuous_update=False,
        )
        self.model_path.observe(self._load_custom_model, "value")

        self.refresh_btn = Button(
            description="Run Pipeline",
            tooltip="Passes text within the current selection into the loaded nlp pipeline and displays the results in a table.",
        )
        self.refresh_btn.on_click(self.refresh)

        self.utils = VBox([self.info, self.model_path, self.refresh_btn])
        self.load_model()

    def _load_custom_model(self, _):
        self.load_model(self.model_path.value)

    def load_model(self, path="en_core_web_sm"):

        # Use the default if the text box is empty
        path = path if path else "en_core_web_sm"

        self.info.clear()
        try:
            self.nlp = spacy.load(path)
            self.info.add(f"Using `{path}`")
            self.refresh_btn.disabled = False
        except:
            self.info.add(f"Failed to load `{path}`", 1)
            self.refresh_btn.disabled = True

    def set_node(self, node):
        self.node = node
        if "spacy-ents" in self.node.data:
            ents = self.node.data["spacy-ents"]
            df = pd.DataFrame(ents)
            self.children = [self.utils, DataFrame(df)]
        else:
            self.children = [self.utils]

    def refresh(self, _=None):
        doc = self.nlp(stringify(self.node))
        ents = defaultdict(int)
        for ent in doc.ents:
            ents[(ent.text, ent.label_)] += 1
        ent_rows = []
        for k, v in ents.items():
            ent_rows.append({"Entity": k[0], "Label": k[1], "Count": v})
        ent_rows.sort(key=lambda x: x["Count"], reverse=True)
        self.node.data["spacy-ents"] = ent_rows
        ents = pd.DataFrame(ent_rows)
        token_df = pd.DataFrame(
            [
                {
                    "TEXT": token.text,
                    "LEMMA": token.lemma_,
                    "POS": token.pos_,
                    "TAG": token.tag_,
                    "DEP": token.dep_,
                }
                for token in doc
            ]
        )

        self.children = [
            VBox([self.utils, DataFrame(ents), DataFrame(token_df)])
        ]


class Cytoscape(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.refresh_btn = SmallButton(
            "refresh", "Recompute network", self.refresh
        )
        self.slider = FloatSlider(0.4, min=0, max=1)
        self.config_btn_recursive = Checkbox(True, description="Recursive")
        self.config_btn_intradoc = Checkbox(
            True, description="Intra-document connections"
        )
        self.export_btn = SmallButton(
            "download", "Save edgelist", self.export_edge_list
        )
        self.children = [
            VBox(
                [
                    self.refresh_btn,
                    self.slider,
                    self.config_btn_recursive,
                    self.config_btn_intradoc,
                    HTML("Hit refresh to generate cytoscape"),
                ]
            )
        ]

    def on_node_click(self, event):
        node = self.node.controller.registry[event["data"]["id"]]
        select(node)
        # self.node.selected = False
        # NODE_REGISTER[event["data"]["id"]].selected = True  # TODO: fix this

    def refresh(self, _=None):
        self.computed_file_path = file_path(self.node)
        self.children = [
            VBox(
                [
                    self.refresh_btn,
                    self.slider,
                    self.config_btn_recursive,
                    self.config_btn_intradoc,
                    HTML("loading..."),
                ]
            )
        ]
        if self.config_btn_recursive.value:
            gen = self.node.controller.dfs(self.node.id)
            next(gen)  # skip first
            docs = {
                node: stringify(node)
                for node in gen
                if node.data["type"] == "section"
            }
        else:
            docs = {
                node: stringify(node)
                for node in immediate_children(self.node)
                if node.data["type"] in ["section", "pdf", "folder"]
            }

        for doc, v in list(docs.items()):
            if v == "":
                docs.pop(doc)

        sim = tfidf_similarity(docs)
        if len(sim) == 0:
            self.children = [
                VBox(
                    [
                        self.refresh_btn,
                        self.slider,
                        self.config_btn_recursive,
                        self.config_btn_intradoc,
                        HTML("Not enough nodes"),
                    ]
                )
            ]
            return

        files = set(
            [file_path(x[0]) for x in sim] + [file_path(x[1]) for x in sim]
        )
        cmap = {k: NODE_COLORS[i] for i, k in enumerate(files)}

        g_edges = []
        self.edges = []
        nodes_with_edges = set()
        for source, target, weight in sim:
            self.edges.append([source.id, target.id, weight])
            if weight > self.slider.value and source.id != target.id:

                if self.config_btn_intradoc.value or file_path(
                    source
                ) != file_path(target):
                    nodes_with_edges.add(source)
                    nodes_with_edges.add(target)
                    g_edges.append(
                        {
                            "data": {
                                "source": source.id,
                                "target": target.id,
                            }
                        }
                    )

        graph_dict = {
            "nodes": [
                {
                    "data": {
                        "id": node.id,
                        "color": cmap[file_path(node)],
                        "name": node.data.get("label", ""),
                    }
                }
                for node in nodes_with_edges
            ],
            "edges": g_edges,
        }

        cyto = CytoscapeWidget()
        cyto.graph.add_graph_from_json(graph_dict)
        cyto.on("node", "click", self.on_node_click)

        self.children = [
            VBox(
                [
                    HBox(
                        [
                            self.export_btn,
                            self.refresh_btn,
                        ]
                    ),
                    self.slider,
                    self.config_btn_recursive,
                    self.config_btn_intradoc,
                    cyto,
                ]
            )
        ]

        cyto.set_style(
            [
                {
                    "selector": "node",
                    "css": {
                        "content": "data(name)",
                        "text-valign": "center",
                        "color": "white",
                        "text-outline-width": 2,
                        "text-outline-color": "black",
                        "background-color": "data(color)",
                    },
                },
                {
                    "selector": ":selected",
                    "css": {
                        "background-color": "data(color)",
                        "line-color": "black",
                        "target-arrow-color": "black",
                        "source-arrow-color": "black",
                        "text-outline-color": "black",
                    },
                },
            ]
        )

    def export_edge_list(self, _=None):
        path = self.computed_file_path
        if path.is_file():
            path = ".".join(str(path).split(".")[:-1])
            path = path + "_edgelist.csv"
        else:
            path = str(path) + "_edgelist.csv"
        with open(path, "w") as f:
            f.write(
                "\n".join([",".join([str(x) for x in e]) for e in self.edges])
            )


class AutoTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.info = Warnings()

        # ---------------------- Settings ----------------------

        self.settings = VBox(
            [
                # No Settings Yet
            ]
        )

        # --------------------- Tesseract ---------------------
        self.tesseract_btn = Button(
            description="Text Only",
            tooltip="Detect and parse text-blocks",
        )
        self.tesseract_btn.on_click(self.extract_text)
        self.te_desc = HTML(
            value=TESS_DESC,
            layout={"width": "400px"},
        )
        self.text_extraction = VBox()
        self.text_extraction.children = [self.te_desc, self.tesseract_btn]

        # --------------------- LayoutParser ---------------------
        self.lp_model = None
        self.layout_extraction = VBox()
        self.layoutparser_btn = Button(
            description="Parse Layout",
            tooltip="Send each page through the Layout Parser pipeline",
        )
        self.layoutparser_btn.on_click(self.extract_layout)

        self.lp_desc = HTML(
            value=LP_DESC,
            layout={"width": "400px"},
        )
        self.layout_extraction.children = [
            self.lp_desc,
            self.layoutparser_btn,
        ]

        self.options = VBox(
            children=[
                self.settings,
                self.info,
                self.text_extraction,
                self.layout_extraction,
            ]
        )

        self.children = [self.options]

    def extract_text(self, btn=None, page_idxs=None):
        """
        Runs each page through Tesseract to get plain text.
        A new monolithic text node is added as a child to the selected node.
        The text can be accessed from the new node's data attribute.

        page_idxs: list of integers
        """
        if isinstance(btn, Button):
            btn.disabled = True
        text_node = {
            "type": "text",
            "parent": self.node.id,
            "children": [],
            "content": [],
        }
        path = file_path(self.node)
        pages = ImageContainer(path, bulk_render=False).info["Pages"]
        if page_idxs is not None:
            pages = [pages[i] for i in page_idxs]
        i = 0
        m = f""
        self.info.add(m)
        for page in get_text_blocks(path):
            i += 1
            self.info.remove(m)
            m = f"Extracting Text: Page {i}/{pages}"
            self.info.add(m)

            for tb in page:
                tb["value"] = tb["value"].strip()
                tb["coords"] = tb.pop("rel_coords")
                tb.pop("pil_coords")
                if tb["value"]:
                    text_node["content"].append(tb)
        self.info.remove(m)
        self.node.controller.insert(text_node, self.node.id)

        if isinstance(btn, Button):
            btn.disabled = False

    def extract_layout(self, btn=None):
        if isinstance(btn, Button):
            btn.disabled = True
        self.layoutparser_btn.disabled = True
        path = file_path(self.node)

        nodes = []

        i = 0
        total = ImageContainer(path, bulk_render=False).info["Pages"]
        m = f"Parsing Layout: {i+1}/{total}"
        self.info.add(m)
        if self.lp_model is None:
            self.lp_model = dd.get_dd_analyzer()
        for layout in parse_layout(path, self.lp_model):
            for block in layout:

                if block.type == "Title":
                    nodes.append(
                        {
                            "id": block.annotation_id,
                            "type": "section",
                            "content": [
                                {
                                    "value": block.text,
                                    "page": i,
                                    "coords": block.relative_coordinates,
                                }
                            ],
                            "label": block.text,
                            "children": block.children,
                        },
                    )
                elif block.type in ["List", "Text"]:
                    nodes.append(
                        {
                            "id": block.annotation_id,
                            "type": "text",
                            "content": [
                                {
                                    "value": block.text,
                                    "page": i,
                                    "coords": block.relative_coordinates,
                                }
                            ],
                            "children": block.children,
                        },
                    )
                elif block.type == "Figure":
                    nodes.append(
                        {
                            "id": block.annotation_id,
                            "type": "image",
                            "content": [
                                {
                                    "value": None,
                                    "page": i,
                                    "coords": block.relative_coordinates,
                                }
                            ],
                            "children": block.children,
                        }
                    )
                elif block.type == "Table":
                    nodes.append(
                        {
                            "id": block.annotation_id,
                            "type": "table",
                            "content": [
                                {
                                    "value": None,
                                    "page": i,
                                    "coords": block.relative_coordinates,
                                }
                            ],
                            "table": block.csv,
                            "children": block.children,
                        }
                    )

            i += 1
            self.info.remove(m)
            m = f"Parsing Layout: {i+1}/{total}"
            self.info.add(m)
        self.info.remove(m)
        self.node.controller.add_multiple(nodes, parent=str(path))

        if isinstance(btn, Button):
            btn.disabled = False


class TableTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.parse_table_btn = Button(
            description="Parse Table (Enclosed Cells)",
            tooltip=(
                "Construct a dataframe from the image. This option works "
                + "well on tables with borders around each cell"
            ),
        )
        self.parse_table_btn.on_click(self.parse_table)
        self.children = [self.parse_table_btn, self.delete_btn]

    def set_node(self, node):
        super().set_node(node)
        if "table" in self.node.data:
            rows = self.node.data["table"]
            if rows:
                df = pd.DataFrame(rows[1:])
                df.columns = rows[0]
            else:
                df = pd.DataFrame(rows)
            self.children = [
                VBox(
                    children=[
                        HBox(children=[self.parse_table_btn, self.delete_btn]),
                        DataFrame(df, max_char=20),
                    ]
                )
            ]
        else:
            self.children = [self.parse_table_btn, self.delete_btn]

    def parse_table(self, _=None):
        path = file_path(self.node)
        imgs = ImageContainer(path, bulk_render=False)
        img = imgs[self.node.data["content"][0]["page"]]
        coords = self.node.data["content"][0]["coords"]

        cropped_img = img.crop(rel_2_pil(coords, img.width, img.height))
        rows = img_2_table(cropped_img)
        self.node.data["table"] = rows

        # Refresh the tab to show the table
        self.set_node(self.node)


import re


class Search(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.results = []  # for API accessibility

        self.input = Text(continuous_update=False)
        self.input.observe(self.search, "value")
        self.partial_search = ToggleButton(
            icon="search",
            layout={"width": "40px"},
            tooltip="Search only the selected node and sub-nodes",
        )
        self.case_match = ToggleButton(
            description="Aa",
            layout={"width": "40px"},
            tooltip="Case Sensitive",
        )
        self.regex = ToggleButton(
            description=".*",
            layout={"width": "40px"},
            tooltip="Regular Expression (certain patterns require case-sensitivity to function properly)",
        )
        self.result_window = VBox()
        search_options = HBox(
            [
                self.case_match,
                self.regex,
                self.partial_search,
            ]
        )
        self.children = [
            VBox([self.input, search_options, self.result_window])
        ]

    def search(self, btn=None, **kwargs):
        """
        kwargs:
            case_sensitive <bool>
            regex <bool>
            query <str>
        """
        # Handle kwargs
        if kwargs.get("case_sensitive"):
            self.case_match.value = kwargs.pop("case_sensitive")
        if kwargs.get("regex"):
            self.regex.value = kwargs.pop("regex")
        if kwargs.get("query"):
            q = kwargs.pop("query")
        else:
            q = self.input.value
        if not q:
            return
        # Format Query based on kwargs
        if not self.case_match.value:
            q = q.lower()
        if not self.regex.value:
            q = re.escape(q)

        # Search for matches
        tree = self.node.controller
        node_id = self.node.id if self.partial_search.value else tree.root.id

        results = []
        exerpts = []
        counts = []

        for n in tree.dfs(node_id):
            c = " ".join(
                [str(c["value"]) or "" for c in n.data.get("content") or []]
            )
            if not self.case_match.value:
                c = c.lower()
            if len(results) == 50:
                break

            count = 0
            exerpt = []
            c = re.sub(r"\s+", " ", c)
            for match in re.finditer(q, c):
                count += 1
                margin = 20
                span = match.span
                g = match.group()
                start, end = match.span()
                exerpt.append(
                    "..."
                    + c[max(0, start - 30) : start]
                    + f"<mark>{g}</mark>"
                    + c[end : end + 30]
                    + "..."
                )
            if count:
                results.append(n)
                counts.append(count)
                exerpts.append("<br>".join(exerpt))

        widgets = []
        for n, t, c in sorted(
            zip(results, exerpts, counts), key=lambda x: x[-1], reverse=True
        ):
            p = natural_path(n)
            btn = Button(description=p, layout={"width": "300px"})
            btn.node = n

            def func(btn):
                #
                btn.node.controller.widget._select_callback(btn.node.id)
                btn.node.controller.widget.goto_node(btn.node.id)

            btn.on_click(func)
            widgets.append(btn)
            widgets.append(HTML(t, layout={"width": "500px"}))

        self.result_window.children = widgets
        self.results = results

from collections import defaultdict
from random import shuffle
from pathlib import Path
import json

import matplotlib.colors as mcolors
import pandas as pd
import pytesseract as tess
import spacy
from ipywidgets import (
    HTML,
    Button,
    Checkbox,
    FloatSlider,
    HBox,
    Tab,
    Textarea,
    VBox,
)
from traitlets import List, link, observe
from ipycytoscape import CytoscapeWidget

from .helper_widgets import (
    RedText,
    ActionRequired,
    ScriptAction,
    CodeBlock,
    SmallButton,
    Warnings,
)
from ..utils.image_utils import (
    ImageContainer,
    cv2_2_rel,
    pil_2_rel,
    rel_2_cv2,
    rel_2_pil,
)
from ..utils.nlp import tfidf_similarity
from ..utils.table_extraction import img_2_table
from ..utils.tess_utils import get_text_blocks
from ..utils.lp_util import parse_layout
from .dataframe_widget import DataFrame
from .doc_tree import NODE_REGISTER, MyNode

NODE_KWARGS = {
    "folder": [0, 5],
    "pdf": [6, 1, 5, 4],
    "section": [1, 5],
    "text": [3, 4],
    "image": [2],
    "table": [7],
}

LP_DESC = ('Layout Extraction will use <a href="htt'
    + 'ps://github.com/Layout-Parser/layout-parser" '
    + 'style="color:blue;">layoutparser</a> to find'
    + " and label images, tables, titles, and normal text within"
    + " the document. Then, the coordinates of each node are used"
    + ' to predict the "natural order" with which the nodes'
    + " would be read.")

TESS_DESC = ('Text Extraction uses <a href="'
    + 'https://github.com/tesseract-ocr/tesseract" '
    + 'style="color:blue;">tesseract</a> to find'
    + " and label textblocks within the document. The order is typically"
    + " more accurate than that of LayoutExtraction. It also tends to "
    + "handle slide shows better than layoutparser as it was trained "
    + "on a much more diverse dataset.")

class NodeDetail(Tab):
    def __init__(self, node):
        super().__init__()
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
            # SectionInsights(node),
            # Summary(node),
        ]
        self.titles = [
            "Info",
            "Tools",
            "ImageTools",
            "TextTools",
            "Spacy",
            "Cytoscape",
            "AutoTools",
            "TableTools"
            # "Insights",
            # "Summary",
        ]

        self.set_title(0, "Info")

    def set_node(self, node):
        self.node = node
        indexes = NODE_KWARGS[self.node._type]
        children = []
        for i in indexes:
            children.append(self.tabs[i])
            if getattr(self.tabs[i], "set_node", False):
                self.tabs[i].set_node(node)
        self.children = children
        for i, j in enumerate(indexes):
            self.set_title(i, self.titles[j])


class MyTab(HBox):
    def __init__(self):
        super().__init__()
        # TODO: when I made this init I thought this would only be run once,
        # that is not the case. Refactor this to only run once.
        self.delete_btn = SmallButton("trash", "Delete this node and all of its children", self.delete_node,"ipypdf-red")

    def add_node(self, btn):
        new_node = MyNode(
            data={
                "type": self._types[btn],
                "path": self.node._path,
                "children": {},
            },
            parent=self.node._id,
        )
        self.node.add_node(new_node)
        new_node.selected = True
        self.node.selected = False

    def set_node(self, node):
        self.node = node

    def delete_node(self, _):
        if self.node._type == "pdf":
            for node in self.node.nodes:
                node.delete()
        else:
            self.node.delete()


class SubsectionTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.text = SmallButton("align-left", "Add a new text node", self.add_node)
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

        text = SmallButton("align-left", "Add a description for the image", self.add_node)

        self._types = {
            text: "text",
        }

        self.children = [text, self.delete_btn]


class TextBlockTools(MyTab):
    content = List(default_value=[]).tag(sync=True)

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.link = link((self.node, "content"), (self, "content"))

    @observe("content")
    def redraw_content(self, _=None):
        self.children = [
            VBox([Textarea(x["value"]) for x in self.node.content]),
            self.delete_btn,
        ]

    def set_node(self, node):
        self.link.unlink()
        self.node = node
        self.link = link((self.node, "content"), (self, "content"))
        self.redraw_content()


class SpacyInsights(MyTab):
    def __init__(self, node):
        super().__init__()
        self._init()

    def _init(self,_=None):
        try:
            self.nlp = spacy.load("en_core_web_lg")
            self.refresh_btn = SmallButton("refresh","Refresh Tables",self.refresh)
            self.utils = HBox([self.refresh_btn])
            self.children = [self.utils]
        except OSError:
            self.children = [
                ScriptAction(
                    message="Spacy en_core_web_lg is required to use this toolkit",
                    args=["spacy","download","en_core_web_lg"],
                    callback=self._init
                )
            ]

    def refresh(self, _=None):
        doc = self.nlp(self.node.stringify())
        ents = defaultdict(int)
        for ent in doc.ents:
            ents[(ent.text, ent.label_)] += 1
        ent_rows = []
        for k, v in ents.items():
            ent_rows.append({"Entity": k[0], "Label": k[1], "Count": v})
        ent_rows.sort(key=lambda x: x["Count"], reverse=True)
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
        self.refresh_btn = SmallButton("refresh", "Recompute network", self.refresh
        )
        self.slider = FloatSlider(0.4, min=0, max=1)
        self.config_btn_recursive = Checkbox(True, description="Recursive")
        self.confib_btn_intradoc = Checkbox(
            True, description="Intra-document connections"
        )
        self.children = [
            VBox(
                [
                    self.refresh_btn,
                    self.slider,
                    self.config_btn_recursive,
                    self.confib_btn_intradoc,
                    HTML("Hit refresh to generate cytoscape"),
                ]
            )
        ]

    def on_node_click(self, event):
        self.node.selected = False
        NODE_REGISTER[event["data"]["id"]].selected = True

    def refresh(self, _=None):

        self.children = [
            VBox(
                [
                    self.refresh_btn,
                    self.slider,
                    self.config_btn_recursive,
                    self.confib_btn_intradoc,
                    HTML("loading..."),
                ]
            )
        ]
        if self.config_btn_recursive.value:
            gen = self.node.dfs()
            next(gen)  # skip first
            docs = {node: node.stringify() for node in gen}
        else:
            docs = {node: node.stringify() for node in self.node.nodes}

        for doc, v in list(docs.items()):
            if v == "" or doc.label == "":
                docs.pop(doc)

        sim = tfidf_similarity(docs)
        if len(sim) == 0:
            self.children = [
                VBox(
                    [
                        self.refresh_btn,
                        self.slider,
                        self.config_btn_recursive,
                        self.confib_btn_intradoc,
                        HTML("Not enough nodes"),
                    ]
                )
            ]
            return

        colors = list(
            mcolors.cnames
        )  # [x.split(":")[1] for x in mcolors.TABLEAU_COLORS]
        shuffle(colors)

        files = set([x._path for x in sim])
        cmap = {k: colors[i] for i, k in enumerate(files)}

        g_edges = []
        pairs = set()
        nodes_with_edges = set()
        for source, edges in sim.items():
            for edge in edges:
                target, weight = edge
                if weight > self.slider.value and source._id != target._id:
                    pair = tuple(sorted([source._id, target._id]))
                    if pair not in pairs:
                        if self.confib_btn_intradoc.value:
                            nodes_with_edges.add(source)
                            nodes_with_edges.add(target)
                            g_edges.append(
                                {
                                    "data": {
                                        "source": source._id,
                                        "target": target._id,
                                    }
                                }
                            )
                            pairs.add(pair)
                        elif source._path != target._path:
                            nodes_with_edges.add(source)
                            nodes_with_edges.add(target)
                            g_edges.append(
                                {
                                    "data": {
                                        "source": source._id,
                                        "target": target._id,
                                    }
                                }
                            )
                            pairs.add(pair)

        graph_dict = {
            "nodes": [
                {
                    "data": {
                        "id": node._id,
                        "color": cmap[node._path],
                        "name": node.label,
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
                    self.refresh_btn,
                    self.slider,
                    self.config_btn_recursive,
                    self.confib_btn_intradoc,
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


class AutoTools(MyTab):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.info = Warnings()

        # ---------------------- Options ----------------------
        self.to_txt = Checkbox(description="Export directly to txt file (needed for large docs)", value=False)
        def warn(e):
            m = f"Warning: output is being piped to {''.join(str(self.node._path).split('.')[:-1])}_output.json"
            if e["new"]:
                self.info.add(m,1)
                # self.layoutparser_btn.disabled = True
                # self.layoutparser_btn.tooltip = "Layout direct to text is not yet supported"
            else:
                self.info.remove(m)
                # self.layoutparser_btn.disabled = False
                # self.layoutparser_btn.tooltip = "Send each page through the LayoutParser pipeline"
            

        self.to_txt.observe(
            warn,
            names="value"
        )
        
        self.settings = VBox([self.to_txt])
        

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
        self.layout_extraction = VBox()
        self.layoutparser_btn = Button(
            description = "Parse Layout",
            tooltip = "Send each page through the LayoutParser pipeline"
        )
        self.layoutparser_btn.on_click(self.extract_layout)

        self.lp_desc = HTML(
            value=LP_DESC,
            layout={"width": "400px"},
        )
        self.init_layoutparser()  # sets children according to layoutparser status

        self.options = VBox(
            children=[
                self.settings,
                self.info,
                self.text_extraction,
                self.layout_extraction,
            ]
        )

        self.children = [self.options]

    def extract_text(self, btn=None):
        if isinstance(btn, Button):
            btn.disabled = True
        text_node = MyNode(
            data={
                "type": "text",
                "path": self.node._path,
                "children": {},
                "content": [],
            },
            parent="" if self.to_txt.value else self.node._id,
        )
        path = self.node._path
        pages = ImageContainer(path, bulk_render=False).info["Pages"]
        i=0
        
        if not self.to_txt.value:
            self.node.add_node(text_node)

        m = f""
        self.info.add(m)
        for page in get_text_blocks(path):
            i+=1
            self.info.remove(m)
            m = f"Extracting Text: Page {i}/{pages}"
            self.info.add(m)

            for tb in page:
                tb["value"] = tb["value"].strip()
                tb["coords"] = tb.pop("rel_coords")
                tb.pop("pil_coords")
                if tb["value"]:
                    text_node.content.append(tb)
        self.info.remove(m)

        if self.to_txt.value:
            fname = f"{'.'.join(str(self.node._path).split('.')[:-1])}_output.json"
            m = f"Writing to: {fname}"
            self.info.add(m)
            with open(fname, "w") as f:
                json.dump(text_node.to_dict(), f)
            text_node.delete()
            self.info.remove(m)


        if isinstance(btn, Button):
            btn.disabled = False

    def extract_layout(self, btn=None):
        if isinstance(btn, Button):
            btn.disabled = True
        self.layoutparser_btn.disabled = True
        path = self.node._path


        # if piping straight to file, then make a detatched node so we don't
        # waste time rendering widgets
        # NOTE: maybe this doesn't work
        root = MyNode(data={"type":"pdf","children":{}}) if self.to_txt.value else self.node
        last_section = root

        i=0
        total = ImageContainer(path, bulk_render=False).info['Pages']
        m = f"Parsing Layout: {i+1}/{total}"
        self.info.add(m)

        for layout in parse_layout(path, self.lp_model):

            for block in layout:

                if block.type == "Title":
                    last_section = MyNode(
                        label=block.text,
                        data={
                            "type": "section",
                            "content": [
                                {
                                    "value": block.text, 
                                    "page": i, 
                                    "coords": block.relative_coordinates
                                }
                            ],
                            "label": block.text,
                        },
                        parent=root._id,
                    )
                    root.add_node(last_section)
                elif block.type in ["List", "Text"]:
                    last_section.add_node(
                        MyNode(
                            data={
                                "type": "text",
                                "content": [
                                    {
                                        "value": block.text, 
                                        "page": i, 
                                        "coords": block.relative_coordinates
                                    }
                                ],
                            },
                            parent=last_section._id,
                        )
                    )
                elif block.type == "Figure":
                    last_section.add_node(
                        MyNode(
                            data={
                                "type": "image",
                                "content": [
                                    {
                                        "value": None,
                                        "page": i,
                                        "coords": block.relative_coordinates,
                                    }
                                ],
                            },
                            parent=last_section._id,
                        )
                    )
                elif block.type == "Table":
                    table_node = MyNode(
                        data={
                            "type": "table",
                            "content": [
                                {
                                    "value": None,
                                    "page": i,
                                    "coords": block.relative_coordinates,
                                }
                            ],
                        },
                        parent=last_section._id,
                    )
                    last_section.add_node(table_node)
                    TableTools(table_node).parse_table()
            
            i+=1
            self.info.remove(m)
            m = f"Parsing Layout: {i+1}/{total}"
            self.info.add(m)
        self.info.remove(m)
        if self.to_txt.value:
            fname = f"{'.'.join(str(self.node._path).split('.')[:-1])}_output.json"
            m = f"Writing to: {fname}"
            self.info.add(m)
            with open(fname, "w") as f:
                json.dump(root.to_dict(), f)
            root.delete()
            self.info.remove(m)

        if isinstance(btn, Button):
            btn.disabled = False

    def init_layoutparser(self,_=None):
        try:
            import layoutparser as lp

            self.lp_model = lp.models.PaddleDetectionLayoutModel(
                "lp://PubLayNet/ppyolov2_r50vd_dcn_365e/config"
            )

            self.layout_extraction.children = [
                self.lp_desc,
                self.layoutparser_btn,
            ]
        except ImportError:
            self.layout_extraction.children = [
                self.lp_desc,
                ScriptAction(
                    message="LayoutParser is not installed",
                    args=["pip","install","layoutparser", "layoutparser[paddledetection]"],
                    callback=self.init_layoutparser
                )
            ]


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
        if len(node.content) > 1:
            rows = node.content[-1]["value"]
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
        path = self.node._path
        imgs = ImageContainer(path, bulk_render=False)
        img = imgs[self.node.content[0]["page"]]
        coords = self.node.content[0]["coords"]

        cropped_img = img.crop(rel_2_pil(coords, img.width, img.height))
        table_coords = rel_2_cv2(coords, img.width, img.height)
        rows = img_2_table(cropped_img)
        for r in rows:
            for cell in r:
                rel_coords = cv2_2_rel(
                    cell[0], img.width, img.height, table_coords
                )
                self.node.content.append(
                    {
                        "value": cell[1],
                        "page": self.node.content[0]["page"],
                        "coords": rel_coords,
                    }
                )
        self.node.content.append(
            {
                "value": [[c[1] for c in r] for r in rows],
                "page": self.node.content[0]["page"],
                "coords": self.node.content[0]["coords"],
            }
        )

        # Refresh the tab to show the table
        self.set_node(self.node)

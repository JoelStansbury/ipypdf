import json
from collections import defaultdict
from pathlib import Path

from ipytree import Node, Tree
from traitlets import List, Unicode, observe

from ..utils.image_utils import rel_2_canvas

NODE_TYPES = {}
NODE_REGISTER = {}
MAX_LEN = 20


def truncate(s: str):
    ellipsis = "..." if len(s) > MAX_LEN else ""
    return s[:MAX_LEN] + ellipsis


NODE_KWARGS = {
    "folder": {
        "icon": "folder",
        "make_dict": False,
        "is_text": False,  # can all content be treated as text
    },
    "pdf": {
        "icon": "file-pdf",
        "make_dict": True,
        "is_text": False,
    },
    "section": {
        "icon": "indent",
        "make_dict": False,
        "is_text": False,
    },
    "text": {
        "icon": "align-left",
        "make_dict": False,
        "is_text": True,
    },
    "image": {
        "icon": "image",
        "make_dict": False,
        "is_text": False,
    },
    "table": {"icon": "table", "make_dict": False, "is_text": False},
}


def node_factory(directory):
    tree = lambda: defaultdict(tree)
    path = Path(directory)
    root_parts = path.parts
    data = tree()
    for x in path.rglob("*.pdf"):
        cursor = data["children"]
        c_path = path
        for part in x.parts[len(root_parts):]:
            c_path = c_path / part
            cursor = cursor[part]

            # Node Attributes
            cursor["path"] = c_path
            set_node_type(cursor, c_path)
            cursor = cursor["children"]

    data["type"] = "folder"
    data["path"] = path
    return MyNode(label=str(directory), data=data)


def set_node_type(cursor, c_path):
    if c_path.is_file():
        if c_path.suffix.lower() == ".pdf":
            cursor["type"] = "pdf"
            if c_path.with_suffix(".json").exists():
                with c_path.with_suffix(".json").open("r") as f:
                    cursor["children"] = json.load(f)
    else:
        cursor["type"] = "folder"


class TreeWidget(Tree):
    def __init__(self, directory: str):
        super().__init__(multiple_selection=False)
        self.add_class("eris-doc-tree")
        self.root = node_factory(directory)
        self.add_node(self.root)
        self.root.collapse_to(2)


class MyNode(Node):
    content = List(default_value=[]).tag(sync=True)
    label = Unicode(default_value="").tag(sync=True)

    def __init__(
        self,
        label="",
        path=None,
        data=None,
        parent=None,
    ):
        super().__init__()
        self._type = data["type"]
        self.content = data.get("content", [])
        NODE_REGISTER[self._id] = self
        self.parent = parent

        # Use the path specified in the data dict if it exists.
        # Otherwise, use the parent's path.
        self._path = data["path"] if "path" in data else path

        self.label = label

        # Visual aspects of the node
        page = f' ({self.content[0]["page"]+1})' if self.content else ""
        self.name = truncate(self.label) + page
        self.icon = NODE_KWARGS[self._type]["icon"]

        if data is not None:
            if isinstance(data["children"], dict):
                for label, d in data["children"].items():
                    self.add_node(
                        MyNode(
                            label=label,
                            path=self._path,
                            data=d,
                            parent=self._id,
                        )
                    )
            elif isinstance(data["children"], list):
                for d in data["children"]:
                    self.add_node(
                        MyNode(
                            label=d["label"],
                            path=self._path,
                            data=d,
                            parent=self._id,
                        )
                    )

    def _delete(self, child):
        self.remove_node(child)

    def delete(self, _=None):
        NODE_REGISTER[self.parent]._delete(self)

    @observe("label")
    def set_name(self, _):
        page = f' ({self.content[0]["page"]+1})' if self.content else ""
        self.name = truncate(self.label) + page

    def add_content(self, item):
        self.content = self.content + [item]

    def collapse_to(self, level):
        if level > 0:
            self.opened = True
            for n in self.nodes:
                n.collapse_to(level - 1)
        else:
            self.opened = False
            for n in self.nodes:
                n.collapse_to(level - 1)

    def get_boxes(self, page_num, w, h, include_children=False):
        bboxes = [
            (rel_2_canvas(c["coords"], w, h), self._type)
            for c in self.content
            if c["page"] == page_num
        ]

        if include_children:
            for child in self.nodes:
                bboxes += child.get_boxes(page_num, w, h, include_children)
        return bboxes

    def _to_dict(self):
        return {
            "label": self.label,
            "content": self.content,
            "type": self._type,
            "children": [c._to_dict() for c in self.nodes],
        }

    def to_dict(self):
        if NODE_KWARGS[self._type]["make_dict"]:
            return {self._path: [c._to_dict() for c in self.nodes]}
        else:
            files = {}
            for c in self.nodes:
                files.update(c.to_dict())
            return files

    def dfs(self):
        """Iterate through all nodes (self included) using depth first search"""
        yield self
        for node in self.nodes:
            yield from node.dfs()

    def stringify(self):
        """
        Recursively construct a monolithic string containing all text
        within this node and all sub-nodes
        """
        if self._type == "text":
            return " ".join([x["value"] for x in self.content])
        content = []
        for c in self.nodes:
            content.append(c.stringify())
        return " ".join(content)

    def to_html(self, level=1):

        """"""
        if self._type == "section":
            s = self.label
            html = f"<h{level}>{s}</h{level}>"
        elif self._type == "text":
            s = " ".join([x["value"] for x in self.content])
            html = (
                s.replace("\n\n", " ")
                .replace("\n", " ")
                .replace("\u00a2", "")
                .replace("\u2014", "")
                .replace("\f", "")
            )
        else:
            html = ""
        for c in self.nodes:
            html += c.to_html(level + 1)
        return html

    def __repr__(self):
        return self.name

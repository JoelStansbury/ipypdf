from pathlib import Path
import json


def file_path(node):
    if node.id == "root":
        return Path(node.data["label"])
    if node.data["type"] == "folder":
        return Path(node.id)
    tree = node.controller
    while ".pdf" not in node.id.lower():
        if node.id == "root":
            return None
        node = tree.parent_of(node)
    return Path(node.id)


def stringify(node):
    result = []
    tree = node.controller
    for n in tree.dfs(node.id):
        if n.data.get("type", None) == "text":
            for c in n.data["content"]:
                result.append(c["value"])
    return " ".join(result)


def select(node):
    tree = node.controller
    select_by_id(tree, node.id)


def _natural_path_backwards(node):
    tree = node.controller
    if node.data["type"] == "pdf":
        return [node.data["label"]]
    else:
        return [node.data.get("label", "")] + _natural_path_backwards(
            tree.parent_of(node)
        )


def natural_path(node):
    bw_path = _natural_path_backwards(node)
    bw_path.reverse()
    return "/".join(bw_path)


def select_by_id(tree, node_id):
    w = tree.widget
    w._select_callback(node_id)
    w.goto_node(node_id)


def immediate_children(node):
    tree = node.controller
    return [tree.registry[node_id] for node_id in node.data["children"]]


def to_dict(node):
    tree = node.controller
    data = []
    for x in tree.dfs(node.id):
        if x.id == node.id:
            pass
        else:
            data.append(x.to_dict())

    return data


def load_from_json(path, parent):
    tree = parent.controller
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        if all(["id" in x for x in data]):
            tree.add_multiple(data, parent.id)
        else:
            tree.insert_nested_dicts(data, parent.id)

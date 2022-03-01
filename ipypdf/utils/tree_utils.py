from pathlib import Path

def file_path(node):
    tree = node.controller
    while '.pdf' not in node.id.lower():
        node = tree.parent_of(node)
    return Path(node.id)

def stringify(node):
    result = []
    tree = node.controller
    for n in tree.dfs(node.id):
        if n.data.get('type', None) == 'text':
            for c in n.data['content']:
                result.append(c['value'])
    return ' '.join(result)


def select(node):
    tree = node.controller
    select_by_id(tree, node.id)

def select_by_id(tree, node_id):
    w = tree.widget
    w._select_callback(node_id)
    w.goto_node(node_id)

def immediate_children(node):
    tree = node.controller
    return [tree.registry[node_id] for node_id in node.data["children"]]
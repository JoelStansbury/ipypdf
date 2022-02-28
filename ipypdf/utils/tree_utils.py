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
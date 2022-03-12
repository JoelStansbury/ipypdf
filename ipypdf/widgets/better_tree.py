# Author: Joel Stansbury
# Email: stansbury.joel@gmail.com 

from pathlib import Path
import time
from uuid import uuid1
import ipywidgets as ipyw
from ipyevents import Event
from traitlets import Unicode, Int, link, observe
from typing import Union, List


CSS = ipyw.HTML("""
    <style>
        .better-tree-btn {
            background: transparent;
            text-align: left;
            width: 200px;
        }
        .better-tree-small {
            text-align: center;
            background: transparent;
            padding:0;
            width: 15px;
        }
        .better-tree-selected {
            background: lightgrey;
            text-align: left;
        }
        .better-tree-box {
            height: -webkit-fill-available;
            width: 250px;
        }
        .better-tree-node-window {
            height: -webkit-fill-available;
            overflow-x: scroll;
        }
        .better-tree-node-row {
            overflow-x: clip;
            width: fit-content;
        }
        .better-tree-slider {
            height: -webkit-fill-available;
            width: 16px;
        }
    </style>
    """)


ICONS = {
    'pdf':'file-pdf',
    'xlsx':'file-excel',
    'xlsm':'file-excel',
    'xls':'file-excel',
    'csv':'file-csv',
    'zip':'file-zipper',
    'gzip':'file-zipper',
    'tar':'file-zipper',
    '7z':'file-zipper',
    'png':'file-image',
    'jpeg':'file-image',
    'jpg':'file-image',
    # Non-extension
    'folder': 'folder',
    'text': 'align-left',
    'table': 'table',
    'image': 'image',
    'section': 'indent',
    
}

class Node:
    def __init__(self, data):
        self.data = data if data else {}
        self.data['children'] = self.data.get('children',[])
        self.id = self.data.get("id", str(uuid1()))
        # self.parent = self.data.get("parent", None)
        self.opened = False
        self.selected = False
    
    def __repr__(self):
        return self.data["label"]
        
    def to_dict(self):
        self.data["id"] = self.id
        self.data["children"] = self.data['children']
        return self.data


class Tree:
    def __init__(self, nodes=None):
        """
        nodes <list[dict]> (None): This must be a flat (not nested) list
            of dictionaries as returned by `Tree.to_dict()`. The nodes
            are added via `Tree.add_multiple(nodes)`
        """
        self.root = Node({'id':'root', 'label':'root'})
        self.root.controller = self
        self.root.level=0
        self.registry = {
            'root':self.root
        }
        self.listeners = []
        self.widget = None
        self.onchange_todos = []

        if nodes:
            self.add_multiple(nodes)

    def _disown(self, node):
        if node.parent is not None:
            old_parent = self.registry[node.parent]
            old_parent.data['children'].remove(node.id)
        node.parent = None
    
    def _set_parent(self, node, parent, position=None):
        if position is None:
            parent.data['children'].append(node.id)
        else:
            parent.data['children'].insert(position, node.id)
        node.parent = parent.id

    def _validate(self):
        for id, node in self.registry.items():
            for c in node.data['children']:
                assert c in self.registry, f"child {c} of {node} does not exist"
                assert self.registry[c].parent == id, \
                    f"child {self.registry[c]} has a different parent: {self.parent_of(c)}.\n" + \
                    f"Should be: {self.registry[id]}"

        for id, node in self.registry.items():
            if id != 'root':
                assert id in self.registry[node.parent].data['children']
 
    def _compute_depth(self, node_id='root', level=0):
        # TODO: Collect some statistics about this. It may actually
        # be more efficient to recompute the depth for the 20
        # visible nodes everytime, versus computing all depths
        # on an alteration
        node = self.registry[node_id]
        node.level = level
        for c in node.data['children']:
            self._compute_depth(c,level+1)

    def onchange(self, function):
        self.onchange_todos.append(function)
    
    def _do_onchange(self):
        if self.widget:
            self.widget.compute_visible()
            # self.widget.refresh()
        for f in self.onchange_todos:
            f()

    def _set_controller(self):
        for id, node in self.registry.items():
            node.controller = self

    def _housekeeping(self):
        # self._validate()
        # self._set_controller()
        self._compute_depth()
        self._do_onchange()

    def _handle_type(self, node:Union[str, Node, dict], allow_creation=False):
        if isinstance(node, str):
            return self.registry[node] 
        if isinstance(node, dict):
            if ('id' in node) and (node["id"] in self.registry):
                return self.registry[node["id"]]
            if allow_creation:
                return Node(node)
        return node

    def parent_of(self, node):
        return self._handle_type(self._handle_type(node).parent)

    def add_node(self, node:Union[Node,dict]):
        """
        add {node.id: node} to the registry
        set parent to 'root' if it is None
        """
        node = self._handle_type(node, allow_creation=True)
        node.controller = self
        assert node.id not in self.registry, "that id is already in use"
        self.registry[node.id] = node
        if node.parent is None:
            self.move(node.id)  # append to children of 'root'
        self._housekeeping()
    
    def get_depth(self, node):
        node = self._handle_type(node)
        return node.parent.level + 1
    
    def add_multiple(
        self,
        node_list: List[Union[Node,dict]],
        parent:Union[str, Node] = 'root'
    ):
        """
        If a node is not present in any of the other provided
        nodes' "children" list, then it is considered an orphan and placed
        directly beneath `parent` (default: 'root').

        every node in `node_list` is required to have a 'children' attribute
        """
        parent = self._handle_type(parent)
        node_list = [
            self._handle_type(node, allow_creation=True)
            for node in node_list
        ]

        ids = set([x.id for x in node_list])
        children = set(sum([x.data['children'] for x in node_list],[]) )
        orphans = ids - children

        for n in node_list:  # preserve the order of node_list
            if n.id in orphans:
                parent.data['children'].append(n.id)

        for node in node_list:
            node.parent = parent.id
            node.controller = self
            self.registry[node.id] = node

        for id, node in self.registry.items():
            for c in node.data['children']:
                self.registry[c].parent = id
        self._housekeeping()
    
    def move(
        self,
        node:Union[str, Node],
        parent:Union[str, Node]='root',
        position: int=None
    ):
        """
        Remove node from current parent's children (if applicable)
        Add node to new parent's children in the correct position
        Set the node's parent attribute to the new parent's id
        """
        node = self._handle_type(node)
        parent = self._handle_type(parent)
        self._disown(node)
        self._set_parent(node, parent, position)
        self._housekeeping()

    def _insert_nested_dict(
        self,
        node_data:dict,
        parent_id:str='root',
        children_key:str='children',
    ):
        # node_data['parent'] = parent_id
        if children_key in node_data:
            children_list = node_data.pop(children_key)
        else:
            children_list = []
        node_data["children"]=[]
        node = Node(node_data)  # get or create node.id
        node.parent = parent_id
        node.controller = self
        self.registry[parent_id].data['children'].append(node.id)
        self.registry[node.id] = node
        for child in children_list:
            self._insert_nested_dict(
                child,parent_id=node.id,children_key=children_key,
            )
 
    def insert_nested_dicts(
        self,
        node_data_list:List[dict],
        parent_id:str=None,
        children_key:str='children',
    ):
        if parent_id is None:
            parent_id = self.root.id
        for node_data in node_data_list:
            self._insert_nested_dict(
                node_data=node_data,
                children_key=children_key,
                parent_id=parent_id
            )
        self._housekeeping()
    
    def insert(self, node_data, parent_id='root'):
        node = Node(node_data)
        node.opened = True
        node.controller = self
        assert node.id not in self.registry
        assert parent_id in self.registry
        self.registry[node.id] = node
        node.parent = parent_id
        self.registry[parent_id].data['children'].append(node.id)
        self._housekeeping()
        return node

    def remove(
        self, 
        node:Union[str, Node],
        recursive:bool=True
    ):
        node = self._handle_type(node)
        if recursive:  # remove children from registry
            for c in list(self.dfs(node.id)):
                self.registry.pop(c.id)
        else:  # move children up
            for c in node.data['children']:
                self.move(c, node.parent)
        
        # remove from parent's children
        self._disown(node)
        self._housekeeping()

    def remove_children(
        self, 
        node:Union[str, Node]
    ):
        node = self._handle_type(node)
        for c in list(self.dfs(node.id))[1:]:
            self.registry.pop(c.id)
        node.data['children'] = []
        self._housekeeping()

    def bfs(self, node_ids:Union[str, List[str]]='root'):
        if isinstance(node_ids, str):
            node_ids = [node_ids]
        for c in node_ids:
            yield self.registry[c]
        next_ids = sum(
            [self.registry[node_id].data['children'] for node_id in node_ids],
            []
        )
        if next_ids:
            yield from self.bfs(next_ids)
    
    def dfs(self, node_id:str='root'):
        yield self.registry[node_id]
        for c in self.registry[node_id].data['children']:
            yield from self.dfs(c)

    def to_list(self, node_id:str='root'):
        result = []
        for node in self.dfs(node_id):
            d = node.to_dict()
            # if d["parent"] == node_id:
            #     d["parent"] = None
            result.append(d)
        return result

    def rglob(self, root, pattern):
        """
        Constructs a tree from an rglob search
        """
        root = Path(root)
        skip = len(root.parts)
        self.registry = {'root':self.root}
        self.root.data['label'] = str(root)
        self.root.data['type'] = 'folder'

        nodes = {'children':[]}
        for p in list(root.rglob(pattern)):
            cursor = nodes
            _id = root
            for part in p.parts[skip:]:
                _id = _id / part
                if not part in [x['label'] for x in cursor["children"]]:
                    _type = 'folder'
                    if len(part.split('.'))>1:
                        _type = part.split('.')[-1]
                    cursor['children'].append(
                        {
                            'id':str(_id),
                            'label':part,
                            'children':[],
                            'type':_type,
                        }
                    )
                cursor = [x for x in cursor["children"] if x['label'] == part][0]
        self.insert_nested_dicts(nodes["children"])

    def __repr__(self, node_id:str='root', level=0):
        collector = f"{' '*level}{self.registry[node_id]}\n"
        for c in self.registry[node_id].data['children']:
            collector += self.__repr__(c, level+1)
        return collector


class TreeWidget(ipyw.VBox):
    selected_id = Unicode(None, allow_none=True)
    def __init__(
        self,
        tree,
        height:int = 25,
    ):
        super().__init__()
        d = Event(
            source=self, 
            watched_events=["wheel"]  #, "mousemove", "mouseleave"]
        )
        d.on_dom_event(self.event_handler)
        self.add_class("better-tree-box")
        self.tree = tree
        self.tree.onchange(self.refresh)
        self.tree.widget = self
        self.rows = [
            NodeWidget(
                self._open_callback,
                self._select_callback,
            ) for i in range(height)
        ]

        for nw in self.rows:
            nw.add_class("better-tree-node-row")

        self.slider = ipyw.IntSlider(
            min=1,
            max=1,  # updated as nodes are opened/closed
            orientation="vertical", 
            readout=False,
        )
        self.slider.add_class("better-tree-slider")

        self.height = height
        self.cursor = 0
        self.selected_node = None

        self.scroll_speed = 1 # set and incrimented in self.scroll
        self.last_deltaY = 0  # attr for deltaY to prevent trackpad accel
        self.trackpad_collector = 0
        self.last_scroll_time = time.time()
        
        self.node_window = ipyw.VBox()
        self.node_window.add_class("better-tree-node-window")

        self._collapse_all()
        self.compute_visible()
        self.refresh()
        
        self.slider.observe(self._slider_onchange, "value")
        full_window = ipyw.HBox([self.slider,self.node_window])
        full_window.add_class("better-tree-box")

        self.children = [full_window, CSS]

    def _collapse_all(self):
        for id, node in self.tree.registry.items():
            node.opened = False
            node.selected = False
        self.tree.root.opened = True
    
    @observe("selected_id", type="change")
    def _update_selected_node(self, event):
        if event["new"]:
            self.selected_node = self.tree.registry[self.selected_id]
    
    def _compute_visible(self, id='root'):
        collector = []
        node = self.tree.registry[id]
        collector.append(node)
        if node.opened:
            for c in node.data['children']:
                collector += self._compute_visible(c)
        return collector
    
    def compute_visible(self):
        self.viewable_nodes = self._compute_visible()
        if len(self.viewable_nodes) > 1:
            previous_max = self.slider.max
            previous_value = self.slider.value
            new_value = len(self.viewable_nodes) - (previous_max - previous_value)
            self.slider.max = len(self.viewable_nodes)
            self.slider.value = new_value
    
    def _compute_inview(self):
        return self.viewable_nodes[self.cursor : self.cursor+self.height]

    def _open_callback(self, id, value):
        self.tree.registry[id].opened = value
        self.compute_visible()
        self.refresh()
        
    def _select_callback(self, id):
        if self.selected_id in self.tree.registry:  # may have been deleted since selection
            self.tree.registry[self.selected_id].selected = False
        self.tree.registry[id].selected = True
        self.selected_id = id
        self.refresh()
        
    def _add_node_callback(self, **kwargs):
        self.tree.add_node(**kwargs)
        self.refresh()

    def scroll(self, val):
        self.cursor += val
        self.cursor = min(self.cursor, len(self.viewable_nodes)-1)
        self.cursor = max(self.cursor, 0)
        self.slider.value = len(self.viewable_nodes) - self.cursor
        # self.refresh()
        # Forces onchange event `_slider_onchange`

    def _slider_onchange(self, event):
        if "new" in event:
            self.goto_index(len(self.viewable_nodes) - event["new"])
        
    def goto_index(self, index):
        self.cursor = index
        self.refresh()

    def goto_node(self, node_id):
        node = self.tree.registry[node_id]
        parent = self.tree.parent_of(node)
        while parent.id != 'root':
            parent.opened = True
            parent = self.tree.parent_of(parent)

        for i, node_id in enumerate(self._compute_visible()):
            if node_id == node.id:
                self.cursor = i
                break
        self.refresh()

    def event_handler(self, event):
        # TODO: add trackpad detection/option
        if "deltaY" in event:
            direction = 1 if event["deltaY"] > 0 else -1
            if (time.time() - self.last_scroll_time < 0.1):  # Accelerate
                self.last_deltaY = event['deltaY']
                self.scroll_speed += 2
                self.last_scroll_time = time.time()
                self.scroll(self.scroll_speed * direction)
            else:  # Reset Speed to 1
                self.scroll_speed = 1
                self.scroll(direction)

    def refresh(self):
        inview = self._compute_inview()
        for i,node in enumerate(inview):
            self.rows[i].load(node)
        self.node_window.children = self.rows[:len(inview)]
            
    
class NodeWidget(ipyw.HBox):
    icon = Unicode("")
    tooltip = Unicode("")
    label = Unicode("")
    indent = Int(0)
    def __init__(
        self,
        _open_callback,
        _select_callback,
    ):
        super().__init__()

        # Callbacks
        self._open_callback = _open_callback
        self._select_callback = _select_callback


        # State Variables
        self.opened = False

        # Widgets
        self.button = ipyw.Button()
        self.expand_btn = ipyw.Button()
        self.html = ipyw.HTML()
        self.indent_box = ipyw.HTML()

        self.children = [
            self.indent_box,
            self.expand_btn,
            self.button,
            self.html
        ]


        # Style
        self.expand_btn.add_class("better-tree-small")
        self.button.add_class("better-tree-btn")

        # Events
            # Button Clicks
        self.button.on_click(self.select)
        self.expand_btn.on_click(self.expand)

            # Traitlets
        link((self, "icon"), (self.button, "icon"))
        link((self, "tooltip"), (self.button, "tooltip"))
        link((self, "label"), (self.html, "value"))
        
    def expand(self, _=None):
        self.opened = not self.opened
        self.expand_btn.icon = 'angle-down' if self.opened else 'angle-right'
        self._open_callback(self.id, self.opened)
        
    def select(self, _=None):
        # self.button.add_class("better-tree-selected")
        self._select_callback(self.id)
        
    def load(self, node):
        self.button.icon = ICONS.get(node.data['type'],"align-justify")
        self.button.description = node.data.get("label","")
        self.indent_box.value = "&nbsp"*node.level*3
        self.opened = node.opened
        if node.data['children']:
            if node.opened:
                self.expand_btn.icon = 'chevron-down' 
            else:
                self.expand_btn.icon = 'chevron-right'
        else:
            self.expand_btn.icon = 'none'

        if node.selected:
            self.button.add_class("better-tree-selected")
        else:
            self.button.remove_class("better-tree-selected")
        
        self.id = node.id

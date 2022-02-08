from json import tool
from ipywidgets import (
    HTML,
    Button,
    HBox,
    VBox,
)
import subprocess
import sys


def add_classes(widget, classes):
    if isinstance(classes,(list,tuple)):
        for c in classes:
            widget.add_class(c)
    elif isinstance(classes, str):
        widget.add_class(classes)


class RedText(HTML):
    def __init__(self, text, extra_classes=None):
        super().__init__(text)
        add_classes(self, extra_classes)
        self.add_class("ipypdf-red")


class CodeBlock(HTML):
    def __init__(self, text, extra_classes=None):
        super().__init__(text)
        add_classes(self, extra_classes)
        self.add_class("ipypdf-code-block")


class SmallButton(Button):
    def __init__(self, icon, tooltip, callback, extra_classes=None):
        super().__init__(icon=icon, tooltip=tooltip)
        add_classes(self, extra_classes)
        self.add_class("ipypdf-small-btn")
        self.on_click(callback)


class ActionRequired(VBox):
    """Red text followed by a HBox of action items"""
    def __init__(self, message:str, actions:dict, callback=None):
        """
        message <str>: Info to show user about the effect of the button
        actions <dict<str,func>>: Btn description text and function callback for each button
        callback <func>: Do this after any button press
        """
        super().__init__()
        btns = []
        for k,v in actions.items():
            btns.append(Button(description=k))
            btns[-1].on_click(v)
            if callback:
                btns[-1].on_click(callback)
        self.children = [RedText(message),HBox(btns)]


class ScriptAction(VBox):
    def __init__(self, message, args, callback=None):
        """
        message <str>: Info to show user about the effect of the button
        args <list<str>>: f'python -m {" ".join(args)}'
        callback <func>: Do this after any button press
        """
        super().__init__()
        cmd = [sys.executable, "-m",] + args
        def func(btn):
            btn.disabled=True
            subprocess.check_call(cmd)
        actions = {"run": lambda btn: func(btn)}
        self.children = [
            ActionRequired(message, actions, callback),
            CodeBlock(" ".join(cmd))
        ]

class Warnings(VBox):
    def __init__(self):
        super().__init__()
        self._warnings = []

    def show(self):
        self._warnings.sort(key=lambda x:x[1], reverse=True)
        self.children = [RedText(m) if s else HTML(m) for m,s in self._warnings]

    def add(self, message, severity=0):
        self._warnings.append((message, severity))
        self.show()
    
    def remove(self, message):
        self._warnings = [x for x in self._warnings if x[0] != message]
        self.show()
    
    def clear(self):
        self._warnings = []
        self.children = []
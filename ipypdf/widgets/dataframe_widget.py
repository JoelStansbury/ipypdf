from collections import deque
from math import ceil

from ipyevents import Event
from ipywidgets import HTML, Button, HBox, VBox
from traitlets import Int, link, observe

CSS = """
    <style>
    .main {
    }
    .content {
        border-top: 1px solid #bdbdbd;
    }
    .row_even {
        background-color:white;
    }
    .row_odd {
        background-color:#f5f5f5;
    }
    .row_hover {
        background-color: #e1f5fe;
    }
    .index {
        font-weight: bold;
    }
    .cell{
        padding: 0 2px 0 0;
        margin: 0;
        text-align: end;
        overflow: hidden !important;
    }
    .header_btn {
        font-weight: bold;
        background-color: inherit;
    }
    </style>
    """


class _Cell(HTML):
    def __init__(self, data, width):
        super().__init__(layout={"width": width})
        self.add_class("cell")
        self.value = str(data)

    def update(self, data):
        self.value = str(data)


class _ButtonCell(Button):
    def __init__(self, data, width, callback, style=None):
        super().__init__(layout={"width": width})
        self.value = data
        self.add_class("cell")
        if style:
            self.add_class(style)
        self.description = str(data)
        self.on_click(callback)


class _Row(HBox):
    value = Int(-1).tag(sync=True)

    def __init__(
        self, data, widths, on_click, style, max_char, _types=None, **kwargs
    ):
        super().__init__(**kwargs)
        self.add_class(style)
        self.observe(on_click, "value")
        d = Event(source=self, watched_events=["click"])
        d.on_dom_event(self.on_click)

        self.max_char = max_char
        self.data = [str(x)[:max_char] for x in data]
        self.cells = [_Cell(x, w) for x, w in zip(self.data, widths)]
        self.cells[0].add_class("index")
        self.children = self.cells

    def update(self, data):
        """Set the cell values to the new `data`"""
        self.data = [str(x)[: self.max_char] for x in data]
        for i, c in enumerate(self.cells):
            c.update(self.data[i])

    def on_click(self, event):
        self.value = -1  # Ensures `value` registers a change event
        # Set self.value to the row index of the dataframe
        self.value = int(self.data[0])


class _Header(HBox):
    def __init__(self, df, widths, content_widget, max_char, **kwargs):
        super().__init__()
        self.df = df
        self.content_widget = content_widget

        def sort_col(btn):
            self.df.sort_values(by=btn.value, inplace=True, kind="mergesort")
            self.content_widget.update()

        def sort_idx(btn):
            self.df.sort_index(inplace=True)
            self.content_widget.idx = 0
            self.content_widget.update()

        col_names = [""] + [str(x) for x in df.columns]
        callbacks = [sort_idx] + [sort_col] * len(df.columns)
        params = zip(col_names, widths, callbacks)

        self.children = [
            _ButtonCell(n, w, cb, style="header_btn") for n, w, cb in params
        ]


class _Content(VBox):
    value = Int(-1).tag(sync=True)
    focus_idx = Int(-1).tag(sync=True)

    def __init__(self, df, to_show, widths, wrap_around, max_char, **kwargs):
        super().__init__(**kwargs)
        self.add_class("content")
        d = Event(
            source=self, watched_events=["wheel", "mousemove", "mouseleave"]
        )
        d.on_dom_event(self.event_handler)

        self.to_show = to_show
        self.num_rows = min(
            len(df), to_show if to_show % 2 == 0 else to_show + 1
        )
        self.idx = 0
        self.wrap_around = wrap_around
        self.df = df
        self.records = df.to_records()

        def row_on_click(event):
            if event["new"] != -1:
                self.value = event["new"]

        self.rows = deque(
            [
                _Row(
                    data=self.records[i],
                    widths=widths,
                    on_click=row_on_click,
                    style=["row_even", "row_odd"][i % 2],
                    max_char=max_char,
                )
                for i in range(self.num_rows)
            ]
        )
        self.children = list(self.rows)[0: self.to_show]

    def update(self, _=None):
        # Need to redo this after sorting ( see _Header.__init__() )
        self.records = self.df.to_records()
        # Update each row
        for i in range(self.num_rows):
            idx = self.idx + i
            self.rows[i].update(self.records[idx])
        self.children = list(self.rows)[0: self.to_show]

    @observe("focus_idx")
    def focus(self, change):
        """Controls the highlighting of rows"""
        old = change["old"]
        new = change["new"]
        if old != -1:
            self.rows[old].remove_class("row_hover")
        if new != -1:
            self.rows[new].add_class("row_hover")

    def on_hover(self, event):
        h = event["boundingRectHeight"]
        row_height = h // min(self.to_show, len(self.df))
        y = event["relativeY"]
        i = int(abs(y // row_height))
        self.focus_idx = min(self.to_show - 1, i)  # Calls self.focus()

    def scroll(self, deltaY):
        N = len(self.records)
        nr = self.num_rows
        self.focus_idx = -1  # Calls self.focus()

        if self.wrap_around:
            n = deltaY
            self.idx += n
            if self.idx >= (N - nr):
                self.idx -= N
            if self.idx <= (-N + 1):
                self.idx += N
        else:
            n = max(min((N - nr) - self.idx, deltaY), -self.idx)
            self.idx += n

        self.rows.rotate(-n)
        if n > 0:
            i = nr - n
            j = nr
        else:
            i = 0
            j = min(abs(n), nr)
        for k in range(i, j):
            x = min(self.idx + k, N - 1)
            self.rows[k].update(self.records[x])
        self.children = [self.rows[i] for i in range(self.to_show)]

    def event_handler(self, event):
        # print(event)
        if "deltaY" in event:
            to_scroll = 1 if event["deltaY"] > 0 else -1
            self.scroll(to_scroll)
        elif "type" in event and event["type"] == "mouseleave":
            self.focus_idx = -1  # Calls self.focus()
        else:
            self.on_hover(event)


class DataFrame(VBox):
    """
    num_rows: (int) number of rows to be displayed
        default: 10
    """

    value = Int().tag(sync=True)

    def __init__(
        self, df, num_rows=10, wrap_around=False, max_char=1000, **kwargs
    ):
        super().__init__(**kwargs)
        self.max_char = max_char

        width, widths = self.auto_width(df, num_rows)

        if not self.layout.width:
            self.layout.width = width

        self.css = HTML(CSS)
        self.add_class("main")
        self.content = _Content(df, num_rows, widths, wrap_around, max_char)
        link((self.content, "value"), (self, "value"))
        self.header = _Header(df, widths, self.content, max_char)
        self.children = [self.header, self.content, self.css]

    def auto_width(self, df, num_rows):
        """
        Uses the first `num_rows` elements of each column to determine
        the width of each row element.
        """

        cols = list(df.columns)
        ppc = 8  # Pixels per Character
        spacing = 2  # Padding (# characters)
        widths = {}

        for c in cols:
            c_width = len(str(c)[: self.max_char])
            d_width = max(
                [len(str(x)[: self.max_char]) for x in df[c].values[:num_rows]]
            )
            widths[c] = max(c_width, d_width) + spacing

        # Make space for index values
        widths["Index"] = len(str(len(df))) + spacing

        # Add index to the list of columns
        cols = ["Index"] + cols
        total = sum(list(widths.values()))

        return f"{total*ppc}px", [
            f"{ceil(100*widths[k]/total)}%" for k in cols
        ]

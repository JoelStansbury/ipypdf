from ipywidgets import Button, Checkbox, HBox


class NavigationToolbar(HBox):
    def __init__(self):
        super().__init__()
        self.prev_page_button = Button(icon="arrow-left")
        self.prev_page_button.add_class("eris-small-btn")
        self.next_page_button = Button(icon="arrow-right")
        self.next_page_button.add_class("eris-small-btn")
        self.draw_bboxes = Checkbox(description="Show Boxes", value=True)
        self.save_button = Button(icon="save")
        self.save_button.add_class("eris-small-btn")
        self.children = [
            self.prev_page_button,
            self.next_page_button,
            self.draw_bboxes,
            self.save_button,
        ]

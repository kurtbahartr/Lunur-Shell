from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from shared import ScrolledView

from utils import KeybindLoader

class KeybindsWidget(ScrolledView):
    def __init__(self, config=None, **kwargs):
        self.loader = KeybindLoader()

        def arrange_func(query: str) -> Iterator[tuple]:
            return self.loader.filter_keybinds(query)

        def add_item_func(item: tuple) -> Button:
            key_combo, commit, cmd = item

            main_label_text = f"{key_combo}   {commit}" if commit else key_combo
            main_label = Label(
                label=main_label_text,
                x_align=0,
                y_align=0.5,
                wrap=False,
                hexpand=True,
                ellipsize=0,
            )

            cmd_label = Label(
                label=cmd,
                x_align=0,
                y_align=0.5,
                wrap=False,
                hexpand=True,
                ellipsize=0,
            )

            box = Box(orientation="horizontal", spacing=8, hexpand=True, halign="start")
            box.add(main_label)
            box.add(cmd_label)

            return Button(
                child=box,
                h_expand=True,
                v_expand=False,
                margin=0,
                padding=0,
                relief="none",
                on_clicked=lambda *_: self.hide(),
                halign="start",
            )

        super().__init__(
            name="keybind-viewer",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            arrange_func=arrange_func,
            add_item_func=add_item_func,
            placeholder="Search Keybinds...",
            min_content_size=(400, 320),
            max_content_size=(800, 600),
            **kwargs,
        )

    def show_all(self):
        self.loader.load_keybinds()
        super().show_all()

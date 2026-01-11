from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from shared.scrolled_view import ScrolledView

from utils.gen_keybinds import KeybindLoader


class KeybindsWidget(ScrolledView):
    def __init__(self, config=None, **kwargs):
        self.loader = KeybindLoader()

        def split_text(text, max_line_length=80):
            words = text.split()
            lines = []
            current_line = []
            for word in words:
                if len(" ".join(current_line + [word])) <= max_line_length:
                    current_line.append(word)
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            return "\n".join(lines)

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

            cmd_wrapped = split_text(cmd, max_line_length=80)
            cmd_label = Label(
                label=cmd_wrapped,
                x_align=0,
                y_align=0.5,
                wrap=False,
                hexpand=True,
                ellipsize=0,
            )

            box = Box(
                orientation="vertical",
                spacing=2,
                hexpand=True,
                halign="start",
                valign="start",
            )
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

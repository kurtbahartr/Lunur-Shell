import json
import subprocess
from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from shared import ScrolledView


modmask_map = {
    64: "SUPER",
    8: "ALT",
    4: "CTRL",
    1: "SHIFT",
}


def modmask_to_key(modmask: int) -> str:
    res = []
    for bf, key in modmask_map.items():
        if modmask & bf == bf:
            res.append(key)
            modmask -= bf
    if modmask != 0:
        res.append(f"({modmask})")
    if len(res) > 0:
        res.append("+ ")
    return " ".join(res)


class KeybindLoader:
    def __init__(self):
        self.keybinds = []

    def load_keybinds(self):
        try:
            output = subprocess.check_output(["hyprctl", "binds", "-j"], text=True)
            binds = json.loads(output)
        except Exception as e:
            print(f"ERROR: Failed to load keybinds from hyprctl: {e}")
            self.keybinds = []
            return

        self.keybinds.clear()
        for bind in binds:
            key_combo = modmask_to_key(bind['modmask']) + bind['key']
            description = bind.get('description', '').strip()
            dispatcher = bind.get('dispatcher', '').strip()
            arg = bind.get('arg', '').strip()
            cmd = f"{dispatcher} {arg}".strip()
            self.keybinds.append((key_combo.strip(), description, cmd))

    def filter_keybinds(self, query: str = "") -> Iterator[tuple]:
        query_cf = query.casefold()
        return (kb for kb in self.keybinds if query_cf in " ".join(kb).casefold())


class KeybindsWidget(ScrolledView):
    def __init__(self, config=None, **kwargs):
        self.loader = KeybindLoader()

        def arrange_func(query: str) -> Iterator[tuple]:
            return self.loader.filter_keybinds(query)

        def add_item_func(item: tuple) -> Button:
            key_combo, commit, cmd = item

            # Combine key combo and description in one label (normal color)
            main_label_text = f"{key_combo}   {commit}" if commit else key_combo
            main_label = Label(
                label=main_label_text,
                x_align=0,
                y_align=0.5,
                wrap=False,
                hexpand=True,
                ellipsize=0,
            )

            # Separate label for cmd (lighter color via CSS nth-child(2))
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

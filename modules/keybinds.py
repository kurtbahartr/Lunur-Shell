from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from shared import ScrolledView
import os
import re

class KeybindLoader:
    def __init__(self, config_path: str):
        self.config_path = os.path.expanduser(config_path)
        self.variables = {}
        self.keybinds = []

    def load_keybinds(self):
        if not os.path.isfile(self.config_path):
            self.keybinds = []
            return

        variable_pattern = re.compile(r"^\s*\$(\w+)\s*=\s*(.*?)(?:\s*#.*)?$")
        bind_pattern = re.compile(r"^\s*(bind[a-z]*)\s*=\s*(.*?)(?:\s*#(.*))?$")

        with open(self.config_path, "r") as f:
            lines = f.readlines()

        self.variables.clear()
        self.keybinds.clear()

        for line in lines:
            if bind_pattern.match(line):
                break
            var_match = variable_pattern.match(line)
            if var_match:
                var_name, var_val = var_match.group(1), var_match.group(2)
                self.variables[var_name] = var_val.strip()

        def expand_vars(text: str) -> str:
            for var, val in self.variables.items():
                text = text.replace(f"${var}", val)
            return text.strip()

        for line in lines:
            m = bind_pattern.match(line)
            if not m:
                continue
            _, remainder, commit = m.group(1), m.group(2), m.group(3) or ""

            parts = []
            current = ""
            in_quotes = False
            for ch in remainder:
                if ch == '"':
                    in_quotes = not in_quotes
                    current += ch
                elif ch == "," and not in_quotes:
                    parts.append(current.strip())
                    current = ""
                else:
                    current += ch
            if current:
                parts.append(current.strip())

            keys_part = parts[:2]
            cmd_part = parts[2:] if len(parts) > 2 else []

            expanded_keys = [expand_vars(k).replace("  ", " ") for k in keys_part if k]
            key_combo = " + ".join(expanded_keys).strip()

            cmd = ", ".join(cmd_part).strip().rstrip(",")

            commit = commit.strip()
            if commit.startswith("$"):
                commit = ""

            self.keybinds.append((key_combo, commit, cmd))

    def filter_keybinds(self, query: str = "") -> Iterator[tuple]:
        query_cf = query.casefold()
        return (kb for kb in self.keybinds if query_cf in " ".join(kb).casefold())

class KeybindsWidget(ScrolledView):
    def __init__(self, config: dict, **kwargs):
        keybinds_cfg = config["keybinds"]
        path = keybinds_cfg["path"]

        self.loader = KeybindLoader(path)

        def arrange_func(query: str) -> Iterator[tuple]:
            return self.loader.filter_keybinds(query)

        def add_item_func(item: tuple) -> Button:
            key_combo, commit, cmd = item
            label_text = f"{key_combo}   {commit}, {cmd}" if commit else f"{key_combo}   {cmd}"

            label = Label(
                label=label_text,
                x_align=0,
                y_align=0.5,
                wrap=False,
                hexpand=True,
                ellipsize=0,
            )

            box = Box(orientation="horizontal", spacing=0, hexpand=True, halign="start")
            box.add(label)

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

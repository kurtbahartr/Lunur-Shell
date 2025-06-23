
from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import idle_add, remove_handler
from gi.repository import GLib

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

        self.variables = {}
        self.keybinds = []

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
            bind_type, remainder, commit = m.group(1), m.group(2), m.group(3) or ""

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

            cmd = ", ".join(cmd_part).strip()
            if cmd.endswith(","):
                cmd = cmd[:-1].strip()

            commit = commit.strip()
            if commit.startswith("$"):
                commit = ""

            self.keybinds.append((key_combo, commit, cmd))

    def filter_keybinds(self, query: str = "") -> Iterator[tuple]:
        query_cf = query.casefold()
        return (
            kb for kb in self.keybinds if query_cf in " ".join(kb).casefold()
        )

class KeybindsWidget(Window):
    def __init__(self, widget_config: dict, **kwargs):
        config_path = widget_config.get("keybinds", "~/.config/hypr/hyprbinds.conf")

        super().__init__(
            name="keybind-viewer",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.loader = KeybindLoader(config_path)
        self._arranger_handler: int = 0

        self.viewport = Box(
            name="keybind-viewer-viewport",
            spacing=2,
            orientation="v",
        )

        self.search_entry = Entry(
            placeholder="Search Keybinds...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
        )

        self.scrolled_window = ScrolledWindow(
            min_content_size=(400, 320),
            max_content_size=(800, 600),
            child=self.viewport,
        )

        self.add(
            Box(
                spacing=2,
                orientation="v",
                style="margin: 2px",
                children=[
                    Box(
                        spacing=2,
                        orientation="h",
                        children=[self.search_entry],
                    ),
                    self.scrolled_window,
                ],
            )
        )

        self.connect("key-press-event", self.on_key_press)

    def show_all(self):
        self.loader.load_keybinds()
        self.search_entry.set_text("")
        self.arrange_viewport()
        super().show_all()
        GLib.idle_add(self.resize_viewport, priority=GLib.PRIORITY_LOW)

    def on_key_press(self, widget, event) -> bool:
        if event.keyval == 65307:  # Escape
            self.hide()
            return True
        return False

    def arrange_viewport(self, query: str = "") -> bool:
        if self._arranger_handler:
            remove_handler(self._arranger_handler)
            self._arranger_handler = 0

        self.viewport.children = []

        filtered_iter = self.loader.filter_keybinds(query)

        self._arranger_handler = idle_add(
            lambda *args: self.add_next_keybind(*args),
            filtered_iter,
            pin=True,
        )

        return False

    def add_next_keybind(self, keybinds_iter: Iterator[tuple]) -> bool:
        item = next(keybinds_iter, None)
        if not item:
            return False

        key_combo, commit, cmd = item

        if commit:
            label_text = f"{key_combo}   {commit}, {cmd}"
        else:
            label_text = f"{key_combo}   {cmd}"

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

        btn = Button(
            child=box,
            h_expand=True,
            v_expand=False,
            margin=0,
            padding=0,
            relief="none",
            on_clicked=lambda *_: self.hide(),
            halign="start",
        )

        self.viewport.add(btn)
        return True

    def resize_viewport(self) -> bool:
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )
        return False

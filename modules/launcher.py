import textwrap
import shutil
from typing import Iterator, Tuple
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.utils import get_desktop_applications
from gi.repository import GdkPixbuf, GLib
from utils.config import widget_config
from shared.scrolled_view import ScrolledView
import utils.functions as helpers
import subprocess
from fabric.utils import logger
from modules.calculator import Calculator


class AppLauncher(ScrolledView):
    def __init__(self, **kwargs):
        config = widget_config["app_launcher"]
        self.app_icon_size = config["app_icon_size"]
        self.show_descriptions = config["show_descriptions"]

        # Pre-allocate list
        self._all_apps: list = []
        self.calculator = Calculator()

        super().__init__(
            name="app-launcher",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            arrange_func=self._arrange_items,
            add_item_func=self._create_item_widget,
            placeholder="Search Applications...",
            min_content_size=(280, 320),
            max_content_size=(560, 320),
            **kwargs,
        )

    def _arrange_items(self, query: str) -> Iterator:
        """Filter items based on query. Optimized for speed."""

        if any(c.isdigit() for c in query):
            calc_result = self.calculator.calculate(query)
            if calc_result is not None:
                yield ("calc", *calc_result)

        query_cf = query.casefold()

        for app in self._all_apps:
            # _search_string is pre-computed. No string concatenation here!
            if query_cf in app._search_string:
                yield app

    def _create_item_widget(self, item) -> Button:
        """Creates the UI row for a search result."""

        if isinstance(item, tuple) and item[0] == "calc":
            return self._build_calc_row(item)

        app = item

        pixbuf = app.get_icon_pixbuf()
        if pixbuf:
            pixbuf = pixbuf.scale_simple(
                self.app_icon_size,
                self.app_icon_size,
                GdkPixbuf.InterpType.BILINEAR,
            )

        labels_box = Box(orientation="v", spacing=2, v_align="center")

        labels_box.add(
            Label(
                label=app.display_name or "Unknown",
                h_align="start",
                v_align="start",
                style="font-weight: bold;",  # Optional styling
            )
        )

        if self.show_descriptions and app.description:
            wrapped_desc = textwrap.fill(app.description, width=60)
            labels_box.add(
                Label(
                    label=wrapped_desc,
                    h_align="start",
                    v_align="start",
                    style="font-size: 0.85em; opacity: 0.7;",
                )
            )

        content_box = Box(
            orientation="h",
            spacing=12,
            children=[
                Image(pixbuf=pixbuf, h_align="start", size=self.app_icon_size),
                labels_box,
            ],
        )

        return Button(
            child=content_box,
            tooltip_text=app.description if self.show_descriptions else None,
            on_clicked=lambda *_: (app.launch(), self.hide()),
        )

    def _build_calc_row(self, item: Tuple) -> Button:
        """Helper to build calculator UI row."""
        _, result, calc_type = item

        content_box = Box(
            orientation="h",
            spacing=12,
            children=[
                Label(
                    label="🔢",
                    h_align="start",
                    v_align="center",
                    style="font-size: 20px;",
                ),
                Box(
                    orientation="v",
                    spacing=2,
                    v_align="center",
                    h_expand=True,
                    children=[
                        Label(
                            label=f"= {result}",
                            h_align="start",
                            v_align="start",
                            style="font-weight: bold;",
                        ),
                        Box(
                            orientation="h",
                            spacing=8,
                            h_expand=True,
                            children=[
                                Label(
                                    label="Click to copy",
                                    h_align="start",
                                    style="font-size: 0.85em; opacity: 0.7;",
                                ),
                                Label(
                                    label=str(calc_type),
                                    h_align="end",
                                    h_expand=True,
                                    style="font-size: 0.85em; opacity: 0.5;",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        return Button(
            child=content_box,
            tooltip_text=f"Copy result: {result}",
            on_clicked=lambda *_: self._copy_to_clipboard(str(result)),
        )

    def _copy_to_clipboard(self, text: str):
        """Optimized clipboard copy."""
        if not shutil.which("wl-copy"):
            logger.error("wl-copy not found. Install wl-clipboard.")
            return

        def copy_task():
            try:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                p.communicate(input=text.encode("utf-8"))

                # Close launcher on success
                GLib.idle_add(self.hide)
            except Exception as e:
                logger.error(f"Clipboard error: {e}")

        # Run in thread to not block UI
        helpers.run_in_thread(copy_task)

    def show_all(self):
        """Refreshes app list and pre-calculates search strings."""
        apps = get_desktop_applications()

        for app in apps:
            if not self.show_descriptions:
                app.description = ""

            app._search_string = (
                f"{app.display_name or ''} {app.name} {app.generic_name or ''}"
            ).casefold()

        self._all_apps = apps
        super().show_all()

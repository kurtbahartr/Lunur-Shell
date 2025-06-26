from typing import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import DesktopApp, get_desktop_applications, idle_add, remove_handler
from gi.repository import GLib, GdkPixbuf
from utils.config import widget_config


class AppLauncher(Window):
    def __init__(self, app_icon_size: int = None, show_descriptions: bool = None, **kwargs):
        config = widget_config["app_launcher"]

        self.app_icon_size = (
            app_icon_size if app_icon_size is not None else config.get("app_icon_size", 48)
        )
        self.show_descriptions = (
            show_descriptions if show_descriptions is not None else config.get("show_descriptions", True)
        )

        super().__init__(
            name="app-launcher",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            **kwargs,
        )
        self.connect("key-press-event", self.on_key_press)

        self._arranger_handler: int = 0
        self._all_apps: list[DesktopApp] = []

        self.viewport = Box(
            name="app-launcher-viewport",
            spacing=2,
            orientation="v",
        )

        self.search_entry = Entry(
            placeholder="Search Applications...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
        )

        self.scrolled_window = ScrolledWindow(
            min_content_size=(280, 320),
            max_content_size=(560, 320),
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

    def show_all(self):
        apps = get_desktop_applications()
        # Optional optimization: strip descriptions if not used
        if not self.show_descriptions:
            for app in apps:
                app.description = ""  # or None if your type allows it
        self._all_apps = apps

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

        filtered_apps = self._filter_apps(query)
        filtered_iter = iter(filtered_apps)

        self._arranger_handler = idle_add(
            lambda *args: self.add_next_application(*args),
            filtered_iter,
            pin=True,
        )

        return False

    def _filter_apps(self, query: str) -> list[DesktopApp]:
        query_cf = query.casefold()
        return [
            app for app in self._all_apps
            if query_cf in f"{app.display_name or ''} {app.name} {app.generic_name or ''}".casefold()
        ]

    def add_next_application(self, apps_iter: Iterator[DesktopApp]) -> bool:
        if not (app := next(apps_iter, None)):
            return False

        self.viewport.add(self.bake_application_slot(app))
        return True

    def resize_viewport(self) -> bool:
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )
        return False

    def bake_application_slot(self, app: DesktopApp, **kwargs) -> Button:
        spacing = max(4, self.app_icon_size // 4)

        pixbuf = app.get_icon_pixbuf()
        if pixbuf is not None:
            pixbuf = pixbuf.scale_simple(
                self.app_icon_size,
                self.app_icon_size,
                GdkPixbuf.InterpType.BILINEAR,
            )

        label_box = [
            Label(
                label=app.display_name or "Unknown",
                h_align="start",
                v_align="start",
            )
        ]

        if self.show_descriptions and app.description:
            label_box.append(
                Label(
                    label=app.description,
                    h_align="start",
                    v_align="start",
                    style="font-size: 10px; color: #888;",
                )
            )

        return Button(
            child=Box(
                orientation="h",
                spacing=12,
                children=[
                    Image(
                        pixbuf=pixbuf,
                        h_align="start",
                        size=self.app_icon_size,
                    ),
                    Box(
                        orientation="v",
                        spacing=2,
                        v_align="center",
                        children=label_box,
                    ),
                ],
            ),
            tooltip_text=app.description if self.show_descriptions else None,
            on_clicked=lambda *_: (app.launch(), self.hide()),
            **kwargs,
        )

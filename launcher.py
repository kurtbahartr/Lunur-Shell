from typing import Iterator
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.utils import get_desktop_applications, DesktopApp
from gi.repository import GdkPixbuf
from utils.config import widget_config
from shared import ScrolledView


class AppLauncher(ScrolledView):
    def __init__(self, **kwargs):
        config = widget_config["app_launcher"]
        self.app_icon_size = config["app_icon_size"]
        self.show_descriptions = config["show_descriptions"]
        self._all_apps: list[DesktopApp] = []

        def arrange_func(query: str) -> Iterator[DesktopApp]:
            query_cf = query.casefold()
            return (
                app for app in self._all_apps
                if query_cf in f"{app.display_name or ''} {app.name} {app.generic_name or ''}".casefold()
            )

        def add_item_func(app: DesktopApp) -> Button:
            pixbuf = app.get_icon_pixbuf()
            if pixbuf is not None:
                pixbuf = pixbuf.scale_simple(
                    self.app_icon_size,
                    self.app_icon_size,
                    GdkPixbuf.InterpType.BILINEAR,
                )

            label_widgets = [
                Label(label=app.display_name or "Unknown", h_align="start", v_align="start")
            ]
            if self.show_descriptions and app.description:
                label_widgets.append(
                    Label(
                        label=app.description,
                        h_align="start",
                        v_align="start",
                        style="font-size: 10px; color: #888;",
                    )
                )

            # The Button itself is the top-level widget returned here
            return Button(
                child=Box(
                    orientation="h",
                    spacing=12,
                    children=[
                        Image(pixbuf=pixbuf, h_align="start", size=self.app_icon_size),
                        Box(orientation="v", spacing=2, v_align="center", children=label_widgets),
                    ],
                ),
                tooltip_text=app.description if self.show_descriptions else None,
                on_clicked=lambda *_: (app.launch(), self.hide()),
            )

        super().__init__(
            name="app-launcher",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            arrange_func=arrange_func,
            add_item_func=add_item_func,
            placeholder="Search Applications...",
            min_content_size=(280, 320),
            max_content_size=(560, 320),
            **kwargs,
        )

    def show_all(self):
        apps = get_desktop_applications()
        if not self.show_descriptions:
            for app in apps:
                app.description = ""
        self._all_apps = apps
        super().show_all()


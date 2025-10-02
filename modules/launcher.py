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
            if pixbuf:
                pixbuf = pixbuf.scale_simple(
                    self.app_icon_size,
                    self.app_icon_size,
                    GdkPixbuf.InterpType.BILINEAR,
                )

            # Labels for app name and optional description
            labels = [Label(label=app.display_name or "Unknown", h_align="start", v_align="start")]
            if self.show_descriptions and app.description:
                def split_description(desc, max_line_length=80):
                    words = desc.split()
                    lines = []
                    current_line = []
                    for word in words:
                        if len(' '.join(current_line + [word])) <= max_line_length:
                            current_line.append(word)
                        else:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(' '.join(current_line))
                    return '\n'.join(lines)
            
                description = split_description(app.description)
                
                labels.append(
                    Label(
                        label=description,
                        h_align="start", 
                        v_align="start",
                    )
                )

            # Compose the button child: horizontal box with icon and vertical labels box
            content_box = Box(
                orientation="h",
                spacing=12,
                children=[
                    Image(pixbuf=pixbuf, h_align="start", size=self.app_icon_size),
                    Box(orientation="v", spacing=2, v_align="center", children=labels),
                ],
            )

            # Return the button widget
            return Button(
                child=content_box,
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
            # Clear descriptions if disabled in config
            for app in apps:
                app.description = ""
        self._all_apps = apps
        super().show_all()

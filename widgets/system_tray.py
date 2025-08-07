import os
import types

import gi
from fabric.utils import bulk_connect
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from gi.repository import Gdk, GdkPixbuf, GLib, Gray, Gtk

from shared import ButtonWidget, Grid, HoverButton, Popover, Separator
from utils import BarConfig
from utils.icons import icons

gi.require_version("Gray", "0.1")


def resolve_icon(item, icon_size: int = 16):
    pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), icon_size)

    try:
        if pixmap is not None:
            return pixmap.as_pixbuf(icon_size, GdkPixbuf.InterpType.HYPER)
        else:
            icon_name = item.get_icon_name()
            icon_theme_path = item.get_icon_theme_path()

            if icon_theme_path:
                custom_theme = Gtk.IconTheme.new()
                custom_theme.prepend_search_path(icon_theme_path)
                try:
                    return custom_theme.load_icon(
                        icon_name,
                        icon_size,
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
                except GLib.Error:
                    return Gtk.IconTheme.get_default().load_icon(
                        icon_name,
                        icon_size,
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
            else:
                if os.path.exists(icon_name):  # for some apps, the icon_name is a path
                    return GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_name, width=icon_size, height=icon_size
                    )
                else:
                    return Gtk.IconTheme.get_default().load_icon(
                        icon_name,
                        icon_size,
                        Gtk.IconLookupFlags.FORCE_SIZE,
                    )
    except GLib.Error:
        return Gtk.IconTheme.get_default().load_icon(
            "image-missing",
            icon_size,
            Gtk.IconLookupFlags.FORCE_SIZE,
        )


class SystemTrayMenu(Box):
    """A widget to display additional system tray items in a grid."""

    def __init__(self, config, **kwargs):
        super().__init__(
            name="system-tray-menu",
            orientation="vertical",
            style_classes=["panel-menu"],
            **kwargs,
        )

        self.config = config
        self._context_menu_open = False

        self.grid = Grid(
            row_spacing=8,
            column_spacing=12,
            margin_top=6,
            margin_bottom=6,
            margin_start=12,
            margin_end=12,
        )
        self.add(self.grid)

        self.row = 0
        self.column = 0
        self.max_columns = 3

    def add_item(self, item):
        button = self.do_bake_item_button(item)

        bulk_connect(
            item,
            {
                "removed": lambda *args: button.destroy(),
                "icon-changed": lambda icon_item: self.do_update_item_button(icon_item, button),
            },
        )

        button.show_all()
        self.grid.attach(button, self.column, self.row, 1, 1)
        self.column += 1
        if self.column >= self.max_columns:
            self.column = 0
            self.row += 1

    def do_bake_item_button(self, item: Gray.Item) -> HoverButton:
        button = HoverButton(
            style_classes="flat",
            tooltip_text=item.get_property("title"),
        )
        button.connect(
            "button-press-event",
            lambda button, event: self.on_button_click(button, item, event),
        )
        self.do_update_item_button(item, button)
        return button

    def do_update_item_button(self, item: Gray.Item, button: HoverButton):
        pixbuf = resolve_icon(item=item)
        button.set_image(Image(pixbuf=pixbuf, pixel_size=self.config["icon_size"]))

    def on_button_click(self, button, item: Gray.Item, event):
        if event.button in (1, 3):
            menu = item.get_property("menu")
            if menu:
                def on_menu_hide(_):
                    self._context_menu_open = False
                    menu.disconnect(on_menu_hide_id)

                on_menu_hide_id = menu.connect("hide", on_menu_hide)
                self._context_menu_open = True

                menu.popup_at_widget(
                    button,
                    Gdk.Gravity.SOUTH,
                    Gdk.Gravity.NORTH,
                    event,
                )
            else:
                self._context_menu_open = True
                item.context_menu(event.x, event.y)

                def reset_flag():
                    self._context_menu_open = False
                    return False

                GLib.timeout_add(1000, reset_flag)

            return True
        return False


class SystemTrayWidget(ButtonWidget):
    """A widget to display the system tray items."""

    MAX_VISIBLE_ICONS = 3

    def __init__(self, widget_config: BarConfig, **kwargs):
        super().__init__(widget_config["system_tray"], name="system_tray", **kwargs)

        self.tray_box = Box(
            spacing=4,
            name="system-tray-box",
            orientation="horizontal",
        )
        self.toggle_icon = Image(
            icon_name=icons["ui"]["arrow"]["down"],
            icon_size=self.config["icon_size"],
            style_classes=["panel-icon", "toggle-icon"],
        )

        self.box.children = (self.tray_box, Separator(), self.toggle_icon)

        self.popup_menu = SystemTrayMenu(config=self.config)
        self.popup = Popover(
            content_factory=lambda: self.popup_menu,
            point_to=self,
        )
        self.popup.connect("popover-closed", self.on_popup_closed)

        # Patch popover focus-out to stay open while context menu is active
        original_focus_out = self.popup._on_popover_focus_out

        def patched_focus_out(self, widget, event):
            if (
                self._content
                and hasattr(self._content, "_context_menu_open")
                and self._content._context_menu_open
            ):
                return True
            return original_focus_out(widget, event)

        self.popup._on_popover_focus_out = types.MethodType(patched_focus_out, self.popup)

        self.watcher = Gray.Watcher()
        self.watcher.connect("item-added", self.on_item_added)

        for item_id in self.watcher.get_items():
            self.on_item_added(self.watcher, item_id)

        self.connect("clicked", self.handle_click)

    def on_popup_closed(self, *_):
        self.toggle_icon.set_from_icon_name(
            icons["ui"]["arrow"]["down"], self.config["icon_size"]
        )
        self.toggle_icon.get_style_context().remove_class("active")

    def handle_click(self, *_):
        visible = self.popup.get_visible()
        if visible:
            self.popup.hide()
            self.toggle_icon.set_from_icon_name(
                icons["ui"]["arrow"]["down"], self.config["icon_size"]
            )
            self.toggle_icon.get_style_context().remove_class("active")
        else:
            self.popup.set_content_factory(lambda: self.popup_menu)
            self.popup._content = None
            self.popup.open()
            self.toggle_icon.set_from_icon_name(
                icons["ui"]["arrow"]["up"], self.config["icon_size"]
            )
            self.toggle_icon.get_style_context().add_class("active")

    def on_item_added(self, _, identifier: str):
        item = self.watcher.get_item_for_identifier(identifier)
        if not item:
            return

        title = item.get_property("title") or ""

        ignored = self.config.get("ignored", [])
        if any(x.lower() in title.lower() for x in ignored):
            return

        hidden = self.config.get("hidden", [])
        if any(x.lower() in title.lower() for x in hidden):
            self.popup_menu.add_item(item)
            self.popup_menu.show_all()
            return

        visible_count = len(self.tray_box.get_children())
        if visible_count < self.MAX_VISIBLE_ICONS:
            button = HoverButton(
                style_classes="flat",
                tooltip_text=title,
                margin_start=2,
                margin_end=2,
            )
            button.connect(
                "button-press-event",
                lambda button, event: self.popup_menu.on_button_click(button, item, event),
            )

            pixbuf = resolve_icon(item=item)
            button.set_image(Image(pixbuf=pixbuf, pixel_size=self.config["icon_size"]))

            item.connect("removed", lambda *args: button.destroy())
            item.connect(
                "icon-changed",
                lambda icon_item: self.popup_menu.do_update_item_button(icon_item, button),
            )

            button.show_all()
            self.tray_box.pack_start(button, False, False, 0)
        else:
            self.popup_menu.add_item(item)
            self.popup_menu.show_all()

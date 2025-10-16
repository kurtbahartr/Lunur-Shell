from gi.repository import Gdk, GLib
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.system_tray import SystemTray, SystemTrayItem
from shared.widget_container import EventBoxWidget
from shared import HoverButton
from utils import BarConfig
from utils.icons import icons
from widgets.common.resolver import (
    resolve_icon,
    create_slide_revealer,
    set_expanded,
    on_leave,
)


class SystemTrayWidget(EventBoxWidget):
    """System tray widget with configurable direction, transition, and tooltip."""

    def __init__(self, widget_config: BarConfig, **kwargs):
        super().__init__(**kwargs)
        self.config = widget_config.get("system_tray", {})
        self.tray_items = {}

        # Config options
        self.icon_size = self.config.get("icon_size", 16)
        self.slide_direction = self.config.get("slide_direction", "left")
        self.transition_duration = self.config.get("transition_duration", 250)
        self.tooltip_enabled = self.config.get("tooltip", True)

        # Toggle icon (arrow)
        arrow_icon_name = "right" if self.slide_direction == "left" else "left"
        self.toggle_icon = Image(
            icon_name=icons["ui"]["arrow"][arrow_icon_name],
            icon_size=self.icon_size,
            style_classes=["panel-icon", "toggle-icon"],
        )

        # Tray box
        self.tray_box = Box(spacing=4, orientation="horizontal")
        self.revealer = create_slide_revealer(
            child=self.tray_box,
            slide_direction=self.slide_direction,
            transition_duration=self.transition_duration,
            initially_revealed=False,
        )

        # Layout setup
        if self.slide_direction == "left":
            self.box.add(self.revealer)
            self.box.add(self.toggle_icon)
        else:
            self.box.add(self.toggle_icon)
            self.box.add(self.revealer)

        self.toggle_icon.show()
        self.revealer.show()
        self.box.show_all()

        # System tray setup
        self.tray = SystemTray()
        self.tray.connect("item_added", self.on_item_added)
        self.tray.connect("item_removed", self.on_item_removed)

        # Populate existing
        for identifier, item in self.tray.items.items():
            self.on_item_added(self.tray, identifier)

        # Hover behavior
        self.connect(
            "enter-notify-event",
            lambda *a: set_expanded(
                self.revealer,
                self.toggle_icon,
                self.slide_direction,
                self.icon_size,
                True,
            ),
        )
        self.connect(
            "leave-notify-event",
            lambda w, e: on_leave(
                w,
                e,
                self.revealer,
                self.slide_direction,
                self.toggle_icon,
                self.icon_size,
            ),
        )

    def on_item_added(self, _, identifier: str):
        item = self.tray.items.get(identifier)
        if not item:
            return

        button = HoverButton(
            tooltip_text=item.title if self.tooltip_enabled else "",
            style_classes="flat",
            margin_start=2,
            margin_end=2,
        )

        # Initial icon
        self._update_item_icon(item, button)

        # Connect click handler
        button.connect(
            "button-press-event", lambda btn, ev: self._on_item_click(btn, item, ev)
        )

        # Connect signals for reactive updates
        signals = ["icon_changed", "updated", "changed"]
        for sig in signals:
            try:
                if hasattr(item, "connect"):
                    item.connect(
                        sig, lambda *a, i=item, b=button: self._update_item_icon(i, b)
                    )
            except Exception:
                pass

        if hasattr(item, "dbus_iface"):
            for sig in ["NewIcon", "AttentionIconChanged"]:
                try:
                    item.dbus_iface.connect_to_signal(
                        sig, lambda *a, i=item, b=button: self._update_item_icon(i, b)
                    )
                except Exception:
                    pass

        self.tray_items[identifier] = (item, button)
        self.tray_box.add(button)
        button.show()

    def _update_item_icon(self, item: SystemTrayItem, button: HoverButton):
        """Update tray icon image for a given item."""
        try:
            pixbuf = resolve_icon(item, self.icon_size)
            if pixbuf:
                image = Image(pixbuf=pixbuf, pixel_size=self.icon_size)
                button.set_image(image)
        except Exception as e:
            print(f"Failed to update icon for {getattr(item, 'title', 'unknown')}: {e}")

    def _on_item_click(self, button, item: SystemTrayItem, event):
        if event.button in (1, 3):
            try:
                if getattr(item, "invoke_menu_for_event", None):
                    item.invoke_menu_for_event(event)
                else:
                    print(
                        f"No menu available for tray item {getattr(item, 'title', '')}"
                    )
            except Exception as e:
                print(f"Error handling tray item click: {e}")
            return True
        return False

    def on_item_removed(self, _, identifier: str):
        entry = self.tray_items.pop(identifier, None)
        if not entry:
            return

        _, button = entry
        self.tray_box.remove(button)
        button.destroy()

        if not self.tray_items:
            set_expanded(
                self.revealer,
                self.toggle_icon,
                self.slide_direction,
                self.icon_size,
                False,
            )

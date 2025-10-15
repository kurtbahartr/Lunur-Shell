from gi.repository import Gdk, GLib
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.system_tray import SystemTray, SystemTrayItem
from shared.widget_container import EventBoxWidget
from shared import HoverButton
from utils import BarConfig
from utils.icons import icons
from widgets.common.resolver import resolve_icon, create_slide_revealer


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
        self.connect("enter-notify-event", lambda *a: self.set_expanded(True))
        self.connect("leave-notify-event", self.on_leave)

        # Optional: periodic check fallback (every 5s)
        GLib.timeout_add_seconds(5, self._check_for_icon_changes)

    def set_expanded(self, expanded: bool):
        """Expand/collapse tray and update arrow."""
        self.revealer.set_reveal_child(expanded)

        if self.slide_direction == "left":
            arrow_icon = "left" if not expanded else "right"
        else:
            arrow_icon = "left" if expanded else "right"

        self.toggle_icon.set_from_icon_name(
            icons["ui"]["arrow"][arrow_icon], self.icon_size
        )

    def on_leave(self, widget, event):
        alloc = self.revealer.get_allocation()
        x, y = widget.translate_coordinates(self.revealer, int(event.x), int(event.y))
        if not (0 <= x <= alloc.width and 0 <= y <= alloc.height):
            self.set_expanded(False)

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

        self._update_item_icon(item, button)

        # Connect click handler
        button.connect(
            "button-press-event", lambda btn, ev: self._on_item_click(btn, item, ev)
        )

        # Connect update signal if available
        if hasattr(item, "connect"):
            try:
                item.connect(
                    "icon_changed", lambda *a: self._update_item_icon(item, button)
                )
                item.connect("updated", lambda *a: self._update_item_icon(item, button))
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
            print(f"Failed to update icon for {item.title}: {e}")

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
            self.set_expanded(False)

    def _check_for_icon_changes(self):
        """Fallback check in case signals aren't emitted when icons change."""
        for identifier, (item, button) in self.tray_items.items():
            try:
                current_pixbuf = resolve_icon(item, self.icon_size)
                if not current_pixbuf:
                    continue

                image_widget = button.get_image()
                if (
                    not image_widget
                    or not image_widget.get_pixbuf()
                    or not image_widget.get_pixbuf().equal(current_pixbuf)
                ):
                    self._update_item_icon(item, button)
            except Exception:
                continue
        return True  # keep checking

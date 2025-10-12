from gi.repository import Gdk
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
        self.tray_items = []

        # Config options
        self.icon_size = self.config.get("icon_size", 16)
        self.slide_direction = self.config.get("slide_direction", "left")
        self.transition_duration = self.config.get("transition_duration", 250)
        self.tooltip_enabled = self.config.get("tooltip", True)

        # Toggle icon (arrow) opposite of slide direction
        arrow_icon_name = "right" if self.slide_direction == "left" else "left"
        self.toggle_icon = Image(
            icon_name=icons["ui"]["arrow"][arrow_icon_name],
            icon_size=self.icon_size,
            style_classes=["panel-icon", "toggle-icon"],
        )

        # Box for tray icons
        self.tray_box = Box(spacing=4, orientation="horizontal")

        self.revealer = create_slide_revealer(
            child=self.tray_box,
            slide_direction=self.slide_direction,
            transition_duration=self.transition_duration,
            initially_revealed=False,
        )

        # Layout: direction determines placement of arrow vs tray
        if self.slide_direction == "left":
            self.box.add(self.revealer)
            self.box.add(self.toggle_icon)
        else:
            self.box.add(self.toggle_icon)
            self.box.add(self.revealer)

        self.toggle_icon.show()
        self.revealer.show()
        self.box.show_all()

        # System tray watcher
        self.tray = SystemTray()
        self.tray.connect("item_added", self.on_item_added)
        self.tray.connect("item_removed", self.on_item_removed)

        # Populate existing items
        for identifier, item in self.tray.items.items():
            self.on_item_added(self.tray, identifier)

        # Hover events to reveal tray
        self.connect("enter-notify-event", lambda *args: self.set_expanded(True))
        self.connect("leave-notify-event", self.on_leave)

    def set_expanded(self, expanded: bool):
        """Show or hide the tray icons and update arrow."""
        self.revealer.set_reveal_child(expanded)

        # Determine arrow icon based on slide direction and expansion state
        if self.slide_direction == "left":
            arrow_icon = "left" if not expanded else "right"
        else:  # right
            arrow_icon = "left" if expanded else "right"

        self.toggle_icon.set_from_icon_name(
            icons["ui"]["arrow"][arrow_icon], self.icon_size
        )

    def on_leave(self, widget, event):
        """Handle mouse leave event to potentially collapse the tray."""
        allocation = self.revealer.get_allocation()
        x, y = widget.translate_coordinates(self.revealer, int(event.x), int(event.y))

        if not (0 <= x <= allocation.width and 0 <= y <= allocation.height):
            self.set_expanded(False)

    def on_item_added(self, _, identifier: str):
        """Add a new system tray item."""
        item = self.tray.items.get(identifier)
        if not item:
            return

        button = HoverButton(
            tooltip_text=item.title if self.tooltip_enabled else "",
            style_classes="flat",
            margin_start=2,
            margin_end=2,
        )

        # Use the custom resolver to load icon safely
        try:
            pixbuf = resolve_icon(item, self.icon_size)
            if pixbuf:
                button.set_image(Image(pixbuf=pixbuf, pixel_size=self.icon_size))
        except Exception as e:
            print(f"Failed to load icon for {item.title}: {e}")

        # Connect left/right click
        button.connect(
            "button-press-event", lambda btn, ev: self._on_item_click(btn, item, ev)
        )

        self.tray_items.append((item, button))
        self.tray_box.add(button)
        button.show()

    def _on_item_click(self, button, item: SystemTrayItem, event):
        """Handle click events on system tray items."""
        if event.button in (1, 3):  # Left or right click
            try:
                # Use invoke_menu_for_event if the item supports it
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
        """Remove a system tray item when it's no longer available."""
        for stored_item, button in self.tray_items[:]:
            if stored_item.identifier == identifier:
                self.tray_box.remove(button)
                self.tray_items.remove((stored_item, button))
                button.destroy()
                break

        # Collapse tray if no items remain
        if not self.tray_items:
            self.set_expanded(False)

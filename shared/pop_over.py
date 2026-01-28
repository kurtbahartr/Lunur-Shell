from typing import ClassVar

import gi
from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.widgets.box import Box
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.widget import Widget
from gi.repository import Gdk, GLib, GObject, GtkLayerShell
from fabric.utils import logger

gi.require_versions(
    {"Gtk": "3.0", "Gdk": "3.0", "GtkLayerShell": "0.1", "GObject": "2.0"}
)


class PopoverManager:
    """Singleton manager to handle shared resources for popovers."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Lazy-initialized overlay window
        self._overlay = None
        self._hyprland_connection = None

        # Keep track of active popovers
        self.active_popover = None
        self.available_windows = []

    @property
    def overlay(self):
        """Lazily create the overlay window on first access."""
        if self._overlay is None:
            self._overlay = WaylandWindow(
                name="popover-overlay",
                style_classes="popover-overlay",
                title="fabric-shell-popover-overlay",
                anchor="left top right bottom",
                margin="-50px 0px 0px 0px",
                exclusivity="auto",
                layer="overlay",
                type="top-level",
                visible=False,
                all_visible=False,
                orientation="h",
            )

            # Add empty box so GTK doesn't complain
            self._overlay.add(Box())

            # Close popover when clicking overlay
            self._overlay.connect("button-press-event", self._on_overlay_clicked)

            # Connect hyprland monitor change handler
            self._hyprland_connection = get_hyprland_connection()
            if self._hyprland_connection:
                self._hyprland_connection.connect(
                    "event::focusedmonv2", self._on_monitor_change
                )

        return self._overlay

    def _on_monitor_change(self, _, event: HyprlandEvent):
        """Close popover when switching monitors."""
        if self.active_popover:
            self.active_popover.hide_popover()
        return True

    def _on_overlay_clicked(self, widget, event):
        """Close popover when clicking the overlay."""
        if self.active_popover:
            self.active_popover.hide_popover()
        return True

    def get_popover_window(self):
        """Get an available popover window or create a new one."""
        if self.available_windows:
            return self.available_windows.pop()

        window = WaylandWindow(
            type="popup",
            layer="overlay",
            name="popover-window",
            anchor="left top",
            visible=False,
            all_visible=False,
            orientation="v",
        )
        GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.ON_DEMAND)
        window.set_keep_above(True)
        return window

    def return_popover_window(self, window):
        """Return a popover window to the pool."""
        # Remove any children
        for child in window.get_children():
            window.remove(child)

        window.hide()

        # Only keep a reasonable number of windows in the pool
        if len(self.available_windows) < 5:
            self.available_windows.append(window)
        else:
            # Let the window be garbage collected
            window.destroy()

    def activate_popover(self, popover):
        """Set the active popover and show overlay."""
        if self.active_popover and self.active_popover != popover:
            self.active_popover.hide_popover()

        self.active_popover = popover
        self.overlay.show()


@GObject.type_register
class Popover(Widget):
    """Memory-efficient popover implementation with pooled windows."""

    __gsignals__: ClassVar = {
        "popover-opened": (GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE, ()),
        "popover-closed": (GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE, ()),
    }

    def __init__(
        self,
        point_to,
        content_factory=None,
        content=None,
    ):
        """
        Initialize a popover.

        Args:
            point_to: Widget to position the popover next to
            content_factory: Function that returns content widget when called
            content: Pre-built content widget (alternative to content_factory)
        """
        super().__init__()

        self._content_factory = content_factory
        self._point_to = point_to
        self._content_window = None
        self._content = content
        self._visible = False
        self._destroy_timeout = None

        # Get singleton manager instance
        self._manager = PopoverManager()

    def set_content_factory(self, content_factory):
        """Set the content factory for the popover."""
        self._content_factory = content_factory

    def set_content(self, content):
        """Set the content for the popover."""
        self._content = content

    def _on_key_press(self, widget, event):
        """Handle Escape key to close popover."""
        if event.keyval == Gdk.KEY_Escape and self._manager.active_popover:
            self._manager.active_popover.hide_popover()
        return False

    def open(self, *_):
        """Open the popover, creating it lazily if needed."""
        # Cancel any pending destroy timeout
        if self._destroy_timeout is not None:
            GLib.source_remove(self._destroy_timeout)
            self._destroy_timeout = None

        if not self._content_window:
            try:
                self._create_popover()
            except Exception as e:
                logger.exception(f"Could not create popover: {e}")
                return
        else:
            self._manager.activate_popover(self)
            self._content_window.show()
            self._visible = True

        self.emit("popover-opened")

    def _calculate_margins(self):
        """Calculate popover position relative to point_to widget."""
        if self._content_window is None:
            return [0, 0, 0, 0]

        widget_allocation = self._point_to.get_allocation()
        popover_allocation = self._content_window.get_allocation()
        popover_width = popover_allocation.width
        popover_height = popover_allocation.height

        display = Gdk.Display.get_default()
        if display is None:
            x = widget_allocation.x
            y = widget_allocation.y - 5
            return [y, 0, 0, x]

        screen = display.get_default_screen()
        if screen is None:
            x = widget_allocation.x
            y = widget_allocation.y - 5
            return [y, 0, 0, x]

        # Get monitor index, then get the geometry from that monitor
        monitor_index = screen.get_monitor_at_window(self._point_to.get_window())
        monitor_geometry = screen.get_monitor_geometry(monitor_index)

        x = widget_allocation.x + (widget_allocation.width / 2) - (popover_width / 2)
        y = widget_allocation.y - 5

        if x <= 0:
            x = widget_allocation.x
        elif x + popover_width >= monitor_geometry.width:
            x = widget_allocation.x - popover_width + widget_allocation.width

        return [y, 0, 0, x]

    def set_position(self, position: tuple[int, int, int, int] | None = None):
        """Set popover position manually or auto-calculate."""
        if self._content_window is None:
            return False

        if position is None:
            self._content_window.set_margin(self._calculate_margins())
        else:
            self._content_window.set_margin(position)
        return False

    def _on_content_ready(self, widget, event):
        """Reposition when content is drawn (fixes calendar positioning)."""
        self.set_position()
        return False

    def _create_popover(self):
        """Create the popover window and add content."""
        # Build content if using factory pattern
        if self._content is None and self._content_factory is not None:
            self._content = self._content_factory()

        if self._content is None:
            raise RuntimeError(
                "Popover content is None and no content_factory provided"
            )

        # Get a window from the pool
        self._content_window = self._manager.get_popover_window()

        # Fix positioning for widgets that render asynchronously (e.g., Gtk.Calendar)
        self._content.connect("draw", self._on_content_ready)

        # Add content to window
        self._content_window.add(
            Box(style_classes="popover-content", children=self._content)
        )

        # Connect event handlers
        self._content_window.connect("focus-out-event", self._on_popover_focus_out)
        self._content_window.connect("key-press-event", self._on_key_press)

        # Activate and show
        self._manager.activate_popover(self)
        self._content_window.show()
        self._visible = True

    def _on_popover_focus_out(self, widget, event):
        """Handle focus loss - close after short delay."""
        GLib.timeout_add(100, self.hide_popover)
        return False

    def hide_popover(self):
        """Hide the popover and schedule cleanup."""
        if not self._visible or not self._content_window:
            return False

        self._content_window.hide()
        self._manager.overlay.hide()
        self._visible = False

        # Schedule destruction after 5 seconds of being hidden
        if not self._destroy_timeout:
            self._destroy_timeout = GLib.timeout_add(5000, self._destroy_popover)

        self.emit("popover-closed")
        return False

    def _destroy_popover(self):
        """Return resources to the pool and clear references."""
        self._destroy_timeout = None
        self._visible = False

        if self._content_window:
            # Return window to the pool
            self._manager.return_popover_window(self._content_window)
            self._content_window = None

        # Allow content to be garbage collected if no longer needed
        self._content = None

        return False

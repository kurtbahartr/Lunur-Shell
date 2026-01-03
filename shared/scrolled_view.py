from typing import Iterator, Callable, Any
from fabric.widgets.box import Box
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import idle_add, remove_handler
from gi.repository import GLib, Gtk, GtkLayerShell

_current_scrolled_view = None  # Global singleton instance tracker


class ScrolledViewManager:
    """Singleton manager to handle overlay for scrolled views."""

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
        self.active_view = None

    @property
    def overlay(self):
        """Lazily create the overlay window on first access."""
        if self._overlay is None:
            self._overlay = Window(
                name="scrolled-view-overlay",
                title="scrolled-view-overlay",
                anchor="left top right bottom",
                margin="0px",
                exclusivity="auto",
                layer="overlay",
                type="top-level",
                visible=False,
                all_visible=False,
            )

            # Add empty box so GTK doesn't complain
            self._overlay.add(Box())

            # Close view when clicking overlay
            self._overlay.connect("button-press-event", self._on_overlay_clicked)

        return self._overlay

    def _on_overlay_clicked(self, widget, event):
        """Close scrolled view when clicking the overlay."""
        if self.active_view:
            self.active_view.hide()
        return True

    def activate_view(self, view):
        """Set the active view and show overlay."""
        if self.active_view and self.active_view != view:
            self.active_view.hide()

        self.active_view = view
        self.overlay.show()

    def deactivate_view(self):
        """Hide overlay when view closes."""
        self.active_view = None
        if self._overlay:
            self._overlay.hide()


class ScrolledView(Window):
    def __init__(
        self,
        *,
        arrange_func: Callable[[str], Iterator[Any]],
        add_item_func: Callable[[Any], Any],
        placeholder: str,
        min_content_size: tuple[int, int],
        max_content_size: tuple[int, int],
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.arrange_func = arrange_func
        self.add_item_func = add_item_func
        self._arranger_handler: int = 0
        self._resized_once = False

        # Get manager instance
        self._manager = ScrolledViewManager()

        self.min_content_size = min_content_size
        self.set_size_request(560, 320)

        # Enable keyboard interaction
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        self.scrolledwindow = Box(spacing=2, orientation="v")
        self.scrolledwindow.set_name("scrolledwindow")

        self.search_entry = Entry(
            placeholder=placeholder,
            h_expand=True,
        )
        self.search_entry.set_name("entry")
        self.search_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.PRIMARY, "system-search"
        )
        self.search_entry.connect(
            "notify::text", lambda entry, *_: self.arrange_viewport(entry.get_text())
        )

        self.viewport = Box(spacing=2, orientation="v")
        self.viewport.set_name("viewport")

        self.displayitems = ScrolledWindow(
            min_content_size=min_content_size,
            max_content_size=max_content_size,
            child=self.viewport,
            h_scrollbar_policy=Gtk.PolicyType.NEVER,
        )
        self.displayitems.set_name("displayitems")

        # Pack widgets
        self.scrolledwindow.add(self.search_entry)
        self.scrolledwindow.add(self.displayitems)
        self.add(self.scrolledwindow)

        # Connect event handlers
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)

    def show_all(self):
        global _current_scrolled_view
        if _current_scrolled_view and _current_scrolled_view is not self:
            _current_scrolled_view.hide()
        _current_scrolled_view = self

        self.search_entry.set_text("")
        self.arrange_viewport()

        # Activate overlay
        self._manager.activate_view(self)

        super().show_all()

        # Focus the search entry
        self.search_entry.grab_focus()

    def hide(self):
        global _current_scrolled_view
        if _current_scrolled_view is self:
            _current_scrolled_view = None

        # Deactivate overlay
        self._manager.deactivate_view()

        super().hide()

    def on_focus_out(self, widget, event):
        """Handle focus loss - close after short delay."""
        GLib.timeout_add(100, self.hide)
        return False

    def on_key_press(self, widget, event) -> bool:
        if event.keyval == 65307:
            self.hide()
            return True
        return False

    def arrange_viewport(self, query: str = "") -> bool:
        if self._arranger_handler:
            remove_handler(self._arranger_handler)
            self._arranger_handler = 0

        # Clear old children safely
        for child in self.viewport.get_children():
            self.viewport.remove(child)

        filtered_iter = self.arrange_func(query)

        self._arranger_handler = idle_add(
            lambda *args: self.add_next_item(*args),
            filtered_iter,
            pin=True,
        )
        return False

    def add_next_item(self, items_iter: Iterator[Any]) -> bool:
        item = next(items_iter, None)
        if not item:
            if not self._resized_once:
                GLib.idle_add(self._resize_to_contents)
                self._resized_once = True
            return False

        widget = self.add_item_func(item)
        self.viewport.add(widget)
        return True

    def _resize_to_contents(self):
        max_width = 0

        for child in self.viewport.get_children():
            _, nat_width = child.get_preferred_width()
            max_width = max(max_width, nat_width)

        max_width += 40
        _, current_height = self.get_size()
        self.set_size_request(max_width, current_height)

from typing import Iterator, Callable, Any
from fabric.widgets.box import Box
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import idle_add, remove_handler
from gi.repository import GLib

_current_scrolled_view = None  # Global singleton instance tracker


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

        self.min_content_size = min_content_size
        self.set_size_request(560, 320)

        self.scrolledwindow = Box(spacing=2, orientation="v")
        self.scrolledwindow.set_name("scrolledwindow")

        # Create Entry widget without notify_text callback first
        self.search_entry = Entry(
            placeholder=placeholder,
            h_expand=True,
        )
        self.search_entry.set_name("entry")

        self.viewport = Box(spacing=2, orientation="v")
        self.viewport.set_name("viewport")

        self.displayitems = ScrolledWindow(
            min_content_size=min_content_size,
            max_content_size=max_content_size,
            child=self.viewport,
        )
        self.displayitems.set_name("displayitems")

        # Pack widgets
        self.scrolledwindow.add(self.search_entry)
        self.scrolledwindow.add(self.displayitems)
        self.add(self.scrolledwindow)

        # Now assign notify_text callback — after viewport is ready!
        self.search_entry.notify_text = lambda entry, *_: self.arrange_viewport(entry.get_text())

        self.connect("key-press-event", self.on_key_press)

    def show_all(self):
        global _current_scrolled_view
        if _current_scrolled_view and _current_scrolled_view is not self:
            _current_scrolled_view.hide()
        _current_scrolled_view = self
        self.search_entry.set_text("")
        self.arrange_viewport()
        super().show_all()

    def hide(self):
        global _current_scrolled_view
        if _current_scrolled_view is self:
            _current_scrolled_view = None
        super().hide()

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

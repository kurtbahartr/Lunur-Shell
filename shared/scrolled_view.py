from typing import Iterator, Callable, Any
from fabric.widgets.box import Box
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import idle_add, remove_handler
from gi.repository import GLib


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

        self.min_content_size = min_content_size
        self.set_size_request(560, 320)

        self.scrolledwindow = Box(spacing=2, orientation="v")
        self.scrolledwindow.set_name("scrolledwindow")

        self.search_entry = Entry(
            placeholder=placeholder,
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
        )
        self.search_entry.set_name("entry")
        self.scrolledwindow.add(self.search_entry)

        self.viewport = Box(spacing=2, orientation="v")
        self.viewport.set_name("viewport")

        self.displayitems = ScrolledWindow(
            min_content_size=min_content_size,
            max_content_size=max_content_size,
            child=self.viewport,
        )
        self.displayitems.set_name("displayitems")
        self.scrolledwindow.add(self.displayitems)

        self.add(self.scrolledwindow)
        self.connect("key-press-event", self.on_key_press)

    def show_all(self):
        self.search_entry.set_text("")
        self.arrange_viewport()
        super().show_all()

    def on_key_press(self, widget, event) -> bool:
        if event.keyval == 65307:
            self.hide()
            return True
        return False

    def arrange_viewport(self, query: str = "") -> bool:
        if self._arranger_handler:
            remove_handler(self._arranger_handler)
            self._arranger_handler = 0

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
            return False
        widget = self.add_item_func(item)
        self.viewport.add(widget)
        return True

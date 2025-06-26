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

        self.viewport = Box(spacing=2, orientation="v")

        self.search_entry = Entry(
            placeholder=placeholder,
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
        )

        self.scrolled_window = ScrolledWindow(
            min_content_size=min_content_size,
            max_content_size=max_content_size,
            child=self.viewport,
        )

        self.add(
            Box(
                spacing=2,
                orientation="v",
                style="margin: 2px",
                children=[
                    Box(spacing=2, orientation="h", children=[self.search_entry]),
                    self.scrolled_window,
                ],
            )
        )

        self.connect("key-press-event", self.on_key_press)

    def show_all(self):
        self.search_entry.set_text("")
        self.arrange_viewport()
        super().show_all()
        GLib.idle_add(self.resize_viewport, priority=GLib.PRIORITY_LOW)

    def on_key_press(self, widget, event) -> bool:
        if event.keyval == 65307:
            self.hide()
            return True
        return False

    def arrange_viewport(self, query: str = "") -> bool:
        if self._arranger_handler:
            remove_handler(self._arranger_handler)
            self._arranger_handler = 0

        self.viewport.children = []

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

    def resize_viewport(self) -> bool:
        self.scrolled_window.set_min_content_width(self.viewport.get_allocation().width)  # type: ignore
        return False


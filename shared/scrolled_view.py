from typing import Iterator, Callable, Any
from fabric.widgets.box import Box
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.utils import idle_add, remove_handler
from gi.repository import Gtk, GtkLayerShell


# --- Click Interceptor Manager ---
class ClickInterceptor:
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

        self._overlay = None
        self._active_view = None

    @property
    def overlay(self):
        if self._overlay is None:
            self._overlay = Window(
                name="click-interceptor-overlay",
                layer="top",
                anchor="left top right bottom",
                margin="-50px",
                exclusivity="auto",
                visible=False,
                all_visible=False,
            )
            self._overlay.add(Box())
            self._overlay.connect("button-press-event", self._on_overlay_clicked)
            GtkLayerShell.set_keyboard_mode(
                self._overlay, GtkLayerShell.KeyboardMode.NONE
            )

        return self._overlay

    def _on_overlay_clicked(self, widget, event):
        if self._active_view:
            self._active_view.hide()
        return True

    def activate(self, view):
        self._active_view = view
        self.overlay.show_all()

    def deactivate(self):
        self._active_view = None
        if self._overlay:
            self._overlay.hide()


# --- Scrolled View ---

_current_scrolled_view = None


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
        kwargs.setdefault("layer", "overlay")
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
            v_scrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        self.displayitems.set_name("displayitems")

        self.scrolledwindow.add(self.search_entry)
        self.scrolledwindow.add(self.displayitems)
        self.add(self.scrolledwindow)

        self.connect("key-press-event", self.on_key_press)

        self._click_interceptor = ClickInterceptor()

    def show_all(self):
        global _current_scrolled_view
        if _current_scrolled_view and _current_scrolled_view is not self:
            _current_scrolled_view.hide()
        _current_scrolled_view = self

        self.search_entry.set_text("")
        self.arrange_viewport()

        self._click_interceptor.activate(self)
        super().show_all()
        self.search_entry.grab_focus()

    def hide(self):
        global _current_scrolled_view
        if _current_scrolled_view is self:
            _current_scrolled_view = None
        self._click_interceptor.deactivate()
        super().hide()

    def on_key_press(self, widget, event) -> bool:
        if event.keyval == 65307:  # Escape key
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

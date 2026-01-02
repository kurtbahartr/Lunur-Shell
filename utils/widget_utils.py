import importlib
from typing import Literal
from fabric.widgets.label import Label
from .icons import icons, text_icons
from gi.repository import Gdk, GLib
from fabric.utils import bulk_connect
from fabric.widgets.image import Image

# Cache for cursors to avoid recreating them
_cursor_cache = {}


def get_cursor(display, cursor_name):
    """Get cached cursor or create new one."""
    if cursor_name not in _cursor_cache:
        _cursor_cache[cursor_name] = Gdk.Cursor.new_from_name(display, cursor_name)
    return _cursor_cache[cursor_name]


# Function to setup cursor hover
def setup_cursor_hover(
    widget, cursor_name: Literal["pointer", "crosshair", "grab"] = "pointer"
):
    display = Gdk.Display.get_default()

    def on_enter_notify_event(widget, _):
        cursor = get_cursor(display, cursor_name)
        widget.get_window().set_cursor(cursor)

    def on_leave_notify_event(widget, _):
        cursor = get_cursor(display, "default")
        widget.get_window().set_cursor(cursor)

    bulk_connect(
        widget,
        {
            "enter-notify-event": on_enter_notify_event,
            "leave-notify-event": on_leave_notify_event,
        },
    )


# Cache for pixbufs to avoid reloading same images
_pixbuf_cache = {}


# Function to get the system icon
def get_icon(app_icon, size=25) -> Image:
    icon_size = size - 5

    if not app_icon:
        return Image(
            name="app-icon",
            icon_name=icons["fallback"]["notification"],
            icon_size=icon_size,
        )

    try:
        # Handle file:// URLs
        if isinstance(app_icon, str) and app_icon.startswith("file://"):
            file_path = app_icon[7:]
            cache_key = (file_path, size)

            if cache_key not in _pixbuf_cache:
                from gi.repository import GdkPixbuf

                _pixbuf_cache[cache_key] = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    file_path, size, size
                )

            return Image(
                name="app-icon",
                pixbuf=_pixbuf_cache[cache_key],
                size=size,
            )

        # Handle absolute file paths
        if isinstance(app_icon, str) and app_icon.startswith("/"):
            cache_key = (app_icon, size)

            if cache_key not in _pixbuf_cache:
                from gi.repository import GdkPixbuf

                _pixbuf_cache[cache_key] = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    app_icon, size, size
                )

            return Image(
                name="app-icon",
                pixbuf=_pixbuf_cache[cache_key],
                size=size,
            )

        # Handle icon names
        return Image(
            name="app-icon",
            icon_name=app_icon,
            icon_size=icon_size,
        )

    except GLib.GError:
        return Image(
            name="app-icon",
            icon_name=icons["fallback"]["notification"],
            icon_size=icon_size,
        )


# Function to create a text icon label
def nerd_font_icon(icon: str, props=None, name="nerd-icon") -> Label:
    label_props = {
        "label": str(icon),
        "name": name,
        "h_align": "center",
        "v_align": "center",
    }

    if props:
        label_props.update(props)

    return Label(**label_props)


def text_icon(icon: str, props=None):
    label_props = {
        "label": icon,
        "name": "nerd-icon",
        "h_align": "center",
        "v_align": "center",
    }

    if props:
        label_props.update(props)

    return Label(**label_props)


# Pre-compute brightness levels for faster lookup
_BRIGHTNESS_LEVELS = [
    (
        0,
        {
            "text_icon": text_icons["brightness"]["off"],
            "icon": icons["brightness"]["off"],
        },
    ),
    (
        32,
        {
            "text_icon": text_icons["brightness"]["low"],
            "icon": icons["brightness"]["low"],
        },
    ),
    (
        66,
        {
            "text_icon": text_icons["brightness"]["medium"],
            "icon": icons["brightness"]["medium"],
        },
    ),
    (
        100,
        {
            "text_icon": text_icons["brightness"]["high"],
            "icon": icons["brightness"]["high"],
        },
    ),
]


# Function to get brightness icon
def get_brightness_icon_name(level: int) -> dict[Literal["icon_text", "icon"], str]:
    for threshold, result in _BRIGHTNESS_LEVELS:
        if level <= threshold:
            return result
    return _BRIGHTNESS_LEVELS[-1][1]


# Pre-compute volume levels for faster lookup
_VOLUME_LEVELS = [
    (
        0,
        {
            "text_icon": text_icons["volume"]["muted"],
            "icon": icons["audio"]["volume"]["muted"],
        },
    ),
    (
        32,
        {
            "text_icon": text_icons["volume"]["low"],
            "icon": icons["audio"]["volume"]["low"],
        },
    ),
    (
        66,
        {
            "text_icon": text_icons["volume"]["medium"],
            "icon": icons["audio"]["volume"]["medium"],
        },
    ),
    (
        100,
        {
            "text_icon": text_icons["volume"]["high"],
            "icon": icons["audio"]["volume"]["high"],
        },
    ),
]

_VOLUME_OVERAMPLIFIED = {
    "text_icon": text_icons["volume"]["overamplified"],
    "icon": icons["audio"]["volume"]["overamplified"],
}


# Function to get volume icon
def get_audio_icon_name(
    volume: int, is_muted: bool
) -> dict[Literal["icon_text", "icon"], str]:
    if is_muted:
        return _VOLUME_LEVELS[0][1]

    if volume > 100:
        return _VOLUME_OVERAMPLIFIED

    for threshold, result in _VOLUME_LEVELS:
        if volume <= threshold:
            return result

    return _VOLUME_LEVELS[-1][1]


# Function to create AnimatedScale
def create_scale(
    name,
    marks=None,
    value=0,
    min_value: float = 0,
    max_value: float = 100,
    increments=(1, 1),
    curve=(0.34, 1.56, 0.64, 1.0),
    orientation="h",
    h_expand=True,
    h_align="center",
    style_classes="",
    duration=0.8,
    **kwargs,
):
    # Import here to avoid circular import
    from shared.animated.scale import AnimatedScale
    from fabric.widgets.scale import ScaleMark

    if marks is None:
        marks = tuple(ScaleMark(value=i) for i in range(1, 100, 10))

    return AnimatedScale(
        name=name,
        marks=marks,
        value=value,
        min_value=min_value,
        max_value=max_value,
        increments=increments,
        orientation=orientation,
        curve=curve,
        h_expand=h_expand,
        h_align=h_align,
        duration=duration,
        style_classes=style_classes,
        **kwargs,
    )


# Cache for imported widget classes
_widget_class_cache = {}


# Function to get the widget class dynamically
def lazy_load_widget(widget_name: str, widgets_list: dict[str, str]):
    # Check cache first
    if widget_name in _widget_class_cache:
        return _widget_class_cache[widget_name]

    if widget_name not in widgets_list:
        raise KeyError(f"Widget {widget_name} not found in the dictionary.")

    class_path = widgets_list[widget_name]
    module_name, class_name = class_path.rsplit(".", 1)

    module = importlib.import_module(module_name)
    widget_class = getattr(module, class_name)

    # Cache the class
    _widget_class_cache[widget_name] = widget_class

    return widget_class

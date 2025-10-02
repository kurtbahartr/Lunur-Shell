import importlib
from typing import Literal
from fabric.widgets.label import Label
from .icons import icons, text_icons
from gi.repository import Gdk, GLib
from fabric.utils import bulk_connect
from fabric.widgets.image import Image

# Function to setup cursor hover
def setup_cursor_hover(
    widget, cursor_name: Literal["pointer", "crosshair", "grab"] = "pointer"
):
    display = Gdk.Display.get_default()

    def on_enter_notify_event(widget, _):
        cursor = Gdk.Cursor.new_from_name(display, cursor_name)
        widget.get_window().set_cursor(cursor)

    def on_leave_notify_event(widget, _):
        cursor = Gdk.Cursor.new_from_name(display, "default")
        widget.get_window().set_cursor(cursor)

    bulk_connect(
        widget,
        {
            "enter-notify-event": on_enter_notify_event,
            "leave-notify-event": on_leave_notify_event,
        },
    )


# Function to get the system icon
def get_icon(app_icon, size=25) -> Image:
    icon_size = size - 5
    try:
        match app_icon:
            case str(x) if "file://" in x:
                from gi.repository import GdkPixbuf

                return Image(
                    name="app-icon",
                    pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_size(
                        app_icon[7:], size, size
                    ),
                    size=size,
                )
            case str(x) if len(x) > 0 and x[0] == "/":
                from gi.repository import GdkPixbuf

                return Image(
                    name="app-icon",
                    pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_size(app_icon, size, size),
                    size=size,
                )
            case _:
                return Image(
                    name="app-icon",
                    icon_name=app_icon
                    if app_icon
                    else icons["fallback"]["notification"],
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
        "label": str(icon),
        "name": "nerd-icon",
        "h_align": "center",
        "v_align": "center",
    }

    if props:
        label_props.update(props)

    return Label(**label_props)


# Function to get brightness icon
def get_brightness_icon_name(level: int) -> dict[Literal["icon_text", "icon"], str]:
    if level <= 0:
        return {
            "text_icon": text_icons["brightness"]["off"],
            "icon": icons["brightness"]["off"],
        }
    if level <= 32:
        return {
            "text_icon": text_icons["brightness"]["low"],
            "icon": icons["brightness"]["low"],
        }
    if level <= 66:
        return {
            "text_icon": text_icons["brightness"]["medium"],
            "icon": icons["brightness"]["medium"],
        }
    return {
        "text_icon": text_icons["brightness"]["high"],
        "icon": icons["brightness"]["high"],
    }


# Function to get volume icon
def get_audio_icon_name(
    volume: int, is_muted: bool
) -> dict[Literal["icon_text", "icon"], str]:
    if volume <= 0 or is_muted:
        return {
            "text_icon": text_icons["volume"]["muted"],
            "icon": icons["audio"]["volume"]["muted"],
        }
    if volume <= 32:
        return {
            "text_icon": text_icons["volume"]["low"],
            "icon": icons["audio"]["volume"]["low"],
        }
    if volume <= 66:
        return {
            "text_icon": text_icons["volume"]["medium"],
            "icon": icons["audio"]["volume"]["medium"],
        }
    if volume <= 100:
        return {
            "text_icon": text_icons["volume"]["high"],
            "icon": icons["audio"]["volume"]["high"],
        }
    return {
        "text_icon": text_icons["volume"]["overamplified"],
        "icon": icons["audio"]["volume"]["overamplified"],
    }


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
        marks = (ScaleMark(value=i) for i in range(1, 100, 10))

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


# Function to get the widget class dynamically
def lazy_load_widget(widget_name: str, widgets_list: dict[str, str]):
    if widget_name in widgets_list:
        class_path = widgets_list[widget_name]
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        widget_class = getattr(module, class_name)
        return widget_class
    else:
        raise KeyError(f"Widget {widget_name} not found in the dictionary.")


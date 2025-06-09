import importlib
from typing import Literal
from fabric.widgets.label import Label
from .icons import icons, text_icons

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

# Function to get the brightness icons
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


# Function to get the volume icons
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


# Function to get the widget class dynamically
def lazy_load_widget(widget_name: str, widgets_list: dict[str, str]):
    if widget_name in widgets_list:
        class_path = widgets_list[widget_name]
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    raise KeyError(f"Widget {widget_name} not found in the dictionary.")


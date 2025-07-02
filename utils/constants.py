from gi.repository import GLib
from typing import TypedDict, List, Dict

APPLICATION_NAME = "Lunur-Shell"
SYSTEM_CACHE_DIR = GLib.get_user_cache_dir()
APP_CACHE_DIRECTORY = f"{SYSTEM_CACHE_DIR}/{APPLICATION_NAME}"


NOTIFICATION_CACHE_FILE = f"{APP_CACHE_DIRECTORY}/notifications.json"

DEFAULT_CONFIG = {
    "date_time": {
        "clock_format": "24h",
        "format": "%b %d", 
    },
    "quick_settings": {
        "icon_size": "16",
        "ignored": [],
        "bar_icons": ["network", "audio", "bluetooth", "brightness"],
        "style_classes": [ "compact" ],
    },
    "keybinds": {
        "enabled": True,
        "path": "~/.config/hypr/hyprbinds.conf",  
    },
    "app_launcher": {
        "icon_size": 16,
        "app_icon_size": 48,
        "show_descriptions": False,
    },
    "general": {
        "layer": "top",
        "location":"top",
        "margin": "6px 6px 0px 6px",  
    },
    "module_groups": [
        {
            "widgets": ["quick_settings", "battery"],
            "spacing": 4,
            "style_classes": ["bordered"],
        },
    ],
    "layout": {
        "left_section": ["app_launcher", "workspaces"],
        "middle_section": ["date_time"],
        "right_section": ["@group:0", "system_tray"],
    },
    "workspaces": {
        "count": 3,
        "hide_unoccupied": False,
        "ignored": [],
        "reverse_scroll": False,
        "empty_scroll": False,
        "default_label_format": "{id}",
        "icon_map": {},  # Example: {"1": "🌐", "2": "🎨"}
    },
    "notification": {
        "enabled": True,
        "anchor": "top-right",
        "auto_dismiss": True,
        "ignored": [],
        "timeout": 3000,
        "max_count": 200,
        "transition_type": "slide-left",
        "transition_duration": 350,
        "per_app_limits": {},
        "play_sound": False,
        "max_actions": 5,
        "dismiss_on_hover": False,
        "sound_file": "notification4",
    },
    "battery": {
        "full_battery_level": 100,
        "hide_label_when_full": True,
        "label": True,
        "tooltip": True,
        "orientation": "vertical",
        "icon_size": 16,
    },
    "system_tray": {
        "icon_size": 16,
        # "ignored": [],
        # "hidden": [],
        # "pinned": [],
        "visible_count": 3,
    },
}

# Other constants
NOTIFICATION_WIDTH = 400
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_ACTION_NUMBER = 3
HIGH_POLL_INTERVAL = 3600  # 1 hour in seconds


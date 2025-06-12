from gi.repository import GLib
from typing import TypedDict, List, Dict

APPLICATION_NAME = "Lunur-Shell"

DEFAULT_CONFIG = {
    "date_time": {
        "clock_format": "24h",
        "format": "%b %d", 
    },
    "app_launcher": {
    },
    "workspaces": {
        "count": 3,
        "hide_unoccupied": True,
        "ignored": [],
        "reverse_scroll": False,
        "empty_scroll": False,
        "default_label_format": "{id}",
        "icon_map": {},  # Example: {"1": "🌐", "2": "🎨"}
    },
    "notifications": {
        "enabled": True,
        "anchor": "top-right",
        "auto_dismiss": True,
        "ignored": [],
        "timeout": 3000,
        "max_count": 5,
    },
    "battery": {
        "full_battery_level": 100,
        "hide_label_when_full": True,
        "label": True,
        "tooltip": True,
        "orientation": "vertical",
        "icon_size": 14,
        "notifications": {
            "enabled": True,
            "discharging": {
                "title": "Charger Unplugged!",
                "body": "Battery is at _LEVEL_%",
            },
            "charging": {
                "title": "Charger Plugged In",
                "body": "Battery is at _LEVEL_%",
            },
        },
    },
}

# Other constants
NOTIFICATION_WIDTH = 400
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_ACTION_NUMBER = 3
HIGH_POLL_INTERVAL = 3600  # 1 hour in seconds


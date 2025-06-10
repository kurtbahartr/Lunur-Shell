from gi.repository import GLib
from typing import TypedDict, List

APPLICATION_NAME = "Lunur-Shell"

DEFAULT_CONFIG = {
    "date_time": {
    },
    "app_launcher": {
    },
    "workspaces": {
    },
    "notifications": {
        "enabled": True,
        "anchor": "top-right",
        "auto_dismiss": True,
        "ignored": [],
        "timeout": 3000,
        "max_count": 5,
    },
}

# Other constants
NOTIFICATION_WIDTH = 400
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_ACTION_NUMBER = 3
HIGH_POLL_INTERVAL = 3600  # 1 hour in seconds


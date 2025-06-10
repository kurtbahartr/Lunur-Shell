from gi.repository import GLib

APPLICATION_NAME = "Lunur-Shell"

DEFAULT_CONFIG = {
    "date_time": {
    },
    "app_launcher": {
    },
    "workspaces": {
    },
    "notifications": {
        "enabled": True
    },
}

# Other constants
NOTIFICATION_WIDTH = 400
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_ACTION_NUMBER = 3
HIGH_POLL_INTERVAL = 3600  # 1 hour in seconds


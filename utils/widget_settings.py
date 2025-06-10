from typing import TypedDict, List, Dict

# Minimal configs for widgets you use

DateTimeMenu = TypedDict(
    "DateTimeMenu",
    {
    },
)

Workspaces = TypedDict(
    "Workspaces",
    {
    },
)

Notifications = TypedDict(
    "Notifications",
    {
        "anchor": str,
        "auto_dismiss": bool,
        "ignored": List[str],
        "timeout": int,
        "max_count": int,
    },
)

Battery = TypedDict(
    "Battery",
    {
        "label": bool,
        "tooltip": bool,
        "orientation": str,
        "full_battery_level": int,
        "hide_label_when_full": bool,
        "icon_size": int,
        "notifications": Dict,
    },
)

# Main minimal BarConfig for your current widgets
class BarConfig(TypedDict):
    date_time: DateTimeMenu
    workspaces: Workspaces
    notifications: Notifications
    battery: Battery


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

# Main minimal BarConfig for your current widgets
class BarConfig(TypedDict):
    date_time: DateTimeMenu
    workspaces: Workspaces
    notifications: Notifications


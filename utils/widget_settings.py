from typing import TypedDict, List, Dict

from .types import Anchor, Layer

DateTimeMenu = TypedDict(
    "DateTimeMenu",
    {
        "clock_format": str,
        "format": str,
    },
)

# Bar configuration
General = TypedDict(
    "General",
    {
        "location": str,
        "layer": Layer,
        "margin": str,
    },
)

AppLauncher = TypedDict(
    "AppLauncher",
    {
        "icon_size": int,
        "app_icon_size": int,
        "show_descriptions": bool,  
    },
)

Workspaces = TypedDict(
    "Workspaces",
    {
        "count": int,
        "hide_unoccupied": bool,
        "ignored": List[int],
        "reverse_scroll": bool,
        "empty_scroll": bool,
        "default_label_format": str,
        "icon_map": Dict[str, str],
    },
)

Notifications = TypedDict(
    "Notifications",
    {
        "enabled": bool,
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

# SystemTray configuration
SystemTray = TypedDict(
    "SystemTray",
    {
        "icon_size": int,
        "ignored": List[str],
        "pinned": List[str],
        "hidden": List[str],
        "visible_count": int,
    },
)

# Quick Settings
QuickSettings = TypedDict(
    "QuickSettings",
    {
        "bar_icons": List[str],
    },
)

Keybinds = TypedDict(
    "Keybinds",
    {
        "enabled": bool,
        "path": str, 
    },
)


# Theme configuration
Theme = TypedDict("Theme", {"name": str})
    
# Main minimal BarConfig for your current widgets
class BarConfig(TypedDict):
    date_time: DateTimeMenu
    workspaces: Workspaces
    notifications: Notifications
    battery: Battery
    system_tray: SystemTray
    quick_settings: QuickSettings
    general: General
    app_launcher: AppLauncher
    keybinds: Keybinds
    theme: Theme

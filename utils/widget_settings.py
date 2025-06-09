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

# Main minimal BarConfig for your current widgets
class BarConfig(TypedDict):
    date_time: DateTimeMenu
    workspaces: Workspaces
    


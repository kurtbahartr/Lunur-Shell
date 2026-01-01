import re

from fabric.hyprland.widgets import HyprlandActiveWindow
from fabric.utils import FormattedString, truncate
from loguru import logger

from shared.widget_container import ButtonWidget
from utils.constants import WINDOW_TITLE_MAP


class WindowTitleWidget(ButtonWidget):
    """a widget that displays the title of the active window."""

    def __init__(self, widget_config=None, **kwargs):
        super().__init__(name="window_title", **kwargs)

        # Store config, defaulting to empty dict if None
        self.widget_config = widget_config or {}

        # Create an ActiveWindow widget to track the active window
        self.window = HyprlandActiveWindow(
            name="window",
            formatter=FormattedString(
                "{ get_title(win_title, win_class) }",
                get_title=self.get_title,
            ),
        )

        # Add the ActiveWindow widget as a child
        self.box.children = self.window

    def get_title(self, win_title: str, win_class: str):
        # Get window_title specific config, or fall back to empty dict
        config = self.widget_config.get("window_title", {})

        trunc = config.get("truncation", True)
        trunc_size = config.get("truncation_size", 50)
        custom_map = config.get("title_map", [])
        icon_enabled = config.get("icon", True)

        win_title = truncate(win_title, trunc_size) if trunc else win_title
        merged_titles = WINDOW_TITLE_MAP + (
            custom_map if isinstance(custom_map, list) else []
        )

        for pattern, icon, name in merged_titles:
            try:
                if re.search(pattern, win_class.lower()):
                    return f"{icon} {name}" if icon_enabled else name
            except re.error as e:
                logger.warning(f"[window_title] Invalid regex '{pattern}': {e}")

        fallback = win_class.lower()
        fallback = truncate(fallback, trunc_size) if trunc else fallback
        return f"󰣆 {fallback}"

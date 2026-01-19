from typing import Iterable

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.widget import Widget

from utils.widget_utils import setup_cursor_hover


class ConfigStyleMixin:
    """
    Mixin to handle config storage and consistent style class merging.
    Used to reduce boilerplate in panel widgets.
    """

    def __init__(
        self,
        style_classes: str | Iterable[str] | None = None,
        default_styles: list[str] | None = None,
        config: dict | None = None,
        **kwargs,
    ):
        # Store config safely
        self.config = config or {}

        # Normalize style_classes to a list and merge with defaults
        final_styles = list(default_styles) if default_styles else []
        if style_classes:
            if isinstance(style_classes, str):
                final_styles.append(style_classes)
            else:
                final_styles.extend(style_classes)

        kwargs["style_classes"] = final_styles
        super().__init__(**kwargs)


class BaseWidget(Widget):
    """A base widget class. Preserved for compatibility with other files."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def toggle(self):
        """Toggle the visibility of the widget."""
        if self.is_visible():
            self.hide()
        else:
            self.show()

    def set_has_class(self, class_name: str | Iterable[str], condition: bool):
        """Conditionally add or remove style classes."""
        if condition:
            self.add_style_class(class_name)
        else:
            self.remove_style_class(class_name)


class ToggleableWidget:
    """
    A lightweight mixin specifically for the toggle behavior.
    Separated to avoid diamond inheritance issues when mixing with Fabric widgets.
    """

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.show()


class BoxWidget(ConfigStyleMixin, ToggleableWidget, Box):
    """A container for box widgets with default styling and config support."""

    def __init__(
        self,
        spacing: int | None = None,
        style_classes: str | list[str] | None = None,
        config: dict | None = None,
        **kwargs,
    ):
        super().__init__(
            spacing=4 if spacing is None else spacing,
            default_styles=["panel-box"],
            style_classes=style_classes,
            config=config,
            **kwargs,
        )


class EventBoxWidget(ConfigStyleMixin, ToggleableWidget, EventBox):
    """A container for eventbox widgets with a default child Box."""

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(default_styles=["panel-eventbox"], config=config, **kwargs)
        self.box = Box(style_classes="panel-box")
        self.add(self.box)


class ButtonWidget(ConfigStyleMixin, ToggleableWidget, Button):
    """A button widget with a default child Box."""

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(default_styles=["panel-button"], config=config, **kwargs)
        self.box = Box()
        self.add(self.box)


class WidgetGroup(BoxWidget):
    """A group of widgets that can be managed and styled together."""

    def __init__(
        self,
        children: list[Widget] | None = None,
        spacing: int = 4,
        style_classes: str | list[str] | None = None,
        config: dict | None = None,
        **kwargs,
    ):
        # Merge WidgetGroup specific styles with user provided styles
        # before passing to BoxWidget (which will add "panel-box")
        merged_styles = ["panel-module-group"]
        if style_classes:
            merged_styles.extend(
                [style_classes] if isinstance(style_classes, str) else style_classes
            )

        super().__init__(
            spacing=spacing,
            style_classes=merged_styles,
            config=config,
            orientation="h",
            **kwargs,
        )

        if children:
            for child in children:
                self.add(child)

    @classmethod
    def from_config(cls, config: dict, widgets_map: dict):
        children = []
        for widget_name in config.get("widgets", []):
            if widget_name in widgets_map:
                widget_configs = config.get("widget_configs", {})
                # Renamed variable to avoid shadowing imported 'widget_config'
                widget_specific_config = widget_configs.get(widget_name, {})
                widget_class = widgets_map[widget_name]
                children.append(widget_class(config=widget_specific_config))

        return cls(
            children=children,
            spacing=config.get("spacing", 4),
            style_classes=config.get("style_classes"),
            config=config,
        )


class HoverButton(Button):
    """A button with hover cursor effects."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        setup_cursor_hover(self)

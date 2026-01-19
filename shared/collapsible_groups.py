from gi.repository import Gtk
from utils.widget_utils import text_icon
from shared.reveal import HoverRevealer


class CollapsibleGroups(HoverRevealer):
    def __init__(
        self,
        collapsed_icon: str,
        child_widgets: list,
        slide_direction: str = "right",
        transition_duration: int = 300,
        spacing: int = 4,
        tooltip: str | None = None,
        icon_size: int = 16,
        **kwargs,
    ):
        icon_widget = text_icon(collapsed_icon, {"size": icon_size})

        children_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
        for widget in child_widgets:
            children_box.add(widget)

        super().__init__(
            visible_child=icon_widget,
            hidden_child=children_box,
            slide_direction=slide_direction,
            transition_duration=transition_duration,
            tooltip=tooltip,
            expanded_margin=16,  # You can customize the slide-out margin here
            **kwargs,
        )

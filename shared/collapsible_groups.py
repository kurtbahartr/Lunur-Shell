from gi.repository import Gtk
from fabric.widgets.revealer import Revealer
from shared.widget_container import ButtonWidget
from utils.widget_utils import text_icon


class CollapsibleGroups(ButtonWidget):
    """A ButtonWidget that collapses multiple child buttons into a single icon and reveals them on hover."""

    def __init__(
        self,
        collapsed_icon: str,
        child_widgets: list,
        slide_direction: str = "right",
        transition_duration: int = 300,
        spacing: int = 4,
        tooltip: str | None = None,
        icon_size: int = 16,
        **kwargs
    ):
        # Initialize ButtonWidget without relying on it creating an icon
        super().__init__(
            tooltip=tooltip or "",
            **kwargs,
        )

        # Create the collapsed icon manually
        self.icon_widget = text_icon(collapsed_icon, {"size": icon_size})

        # Box of child widgets to reveal
        children_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
        for widget in child_widgets:
            children_box.add(widget)

        # Convert direction to Gtk style
        gtk_direction = "slide_right" if slide_direction == "right" else "slide_left"

        # Revealer for child widgets
        self.revealer = Revealer(
            child=children_box,
            transition_type=gtk_direction,
            transition_duration=transition_duration,
            reveal_child=False,
        )

        # Pack icon and revealer according to slide_direction
        if slide_direction == "right":
            self.box.add(self.icon_widget)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(self.icon_widget)

        # Show widgets
        self.icon_widget.show()
        self.revealer.show()
        self.box.show_all()

        # Mouse hover events
        self.connect("enter-notify-event", lambda *_: self.revealer.set_reveal_child(True))
        self.connect("leave-notify-event", lambda *_: self.revealer.set_reveal_child(False))


from gi.repository import Gtk, GLib
from fabric.widgets.revealer import Revealer
from shared.widget_container import EventBoxWidget
from utils.widget_utils import text_icon


class CollapsibleGroups(EventBoxWidget):
    """A collapsible group with child widgets that reveal on hover and respond to clicks."""

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
        super().__init__(tooltip=tooltip or "", **kwargs)

        self.slide_direction = slide_direction
        self.transition_duration = transition_duration

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

        # Mouse hover events to trigger reveal
        self.connect("enter-notify-event", lambda *_: self.set_expanded(True))
        self.connect("leave-notify-event", self.on_leave)

        # Handle click event to toggle the visibility of child widgets
        self.connect("button-press-event", self.on_click)

    def set_expanded(self, expanded: bool):
        """Reveal or hide child widgets and adjust spacing."""
        if expanded:
            if self.slide_direction == "right":
                self.revealer.set_margin_start(16)
                self.revealer.set_margin_end(0)
            else:
                self.revealer.set_margin_start(0)
                self.revealer.set_margin_end(16)
        else:
            # Remove spacing immediately for smoother collapse
            self.revealer.set_margin_start(0)
            self.revealer.set_margin_end(0)

        self.revealer.set_reveal_child(expanded)

    def on_leave(self, widget, event):
        """Don't hide the revealer immediately when the mouse leaves."""
        allocation = self.revealer.get_allocation()

        if not (allocation.x <= event.x <= allocation.x + allocation.width and
                allocation.y <= event.y <= allocation.y + allocation.height):
            self.set_expanded(False)

    def on_click(self, widget, event):
        """Handle the click event to toggle the visibility of the child widgets."""
        if event.button == 1:  # Left-click (button 1)
            self.set_expanded(not self.revealer.get_reveal_child())

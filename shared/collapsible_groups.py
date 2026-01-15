from gi.repository import Gtk, GLib, Gdk
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

        self.icon_widget = text_icon(collapsed_icon, {"size": icon_size})

        children_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
        for widget in child_widgets:
            children_box.add(widget)

        gtk_direction = "slide_right" if slide_direction == "right" else "slide_left"

        self.revealer = Revealer(
            child=children_box,
            transition_type=gtk_direction,
            transition_duration=transition_duration,
            reveal_child=False,
        )

        if slide_direction == "right":
            self.box.add(self.icon_widget)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(self.icon_widget)

        self.icon_widget.show()
        self.revealer.show()
        self.box.show_all()

        self.connect("enter-notify-event", lambda *_: self.set_expanded(True))
        # Connect to the revealer as well to capture mouse moving inside revealed children
        self.revealer.connect("enter-notify-event", lambda *_: self.set_expanded(True))

        self.connect("leave-notify-event", self.on_leave)
        self.revealer.connect("leave-notify-event", self.on_leave)

        self.connect("button-press-event", self.on_click)

    def set_expanded(self, expanded: bool):
        """Reveal or hide child widgets and adjust spacing."""
        if expanded:
            margin = 16
        else:
            margin = 0

        if self.slide_direction == "right":
            self.revealer.set_margin_start(margin)
            self.revealer.set_margin_end(0)
        else:
            self.revealer.set_margin_start(0)
            self.revealer.set_margin_end(margin)

        self.revealer.set_reveal_child(expanded)

    def on_leave(self, widget, event):
        if event.detail == Gdk.NotifyType.INFERIOR:
            return

        # Optional: Add a small timeout/delay here if you want it to feel less "snappy" when closing
        self.set_expanded(False)

    def on_click(self, widget, event):
        """Handle the click event to toggle the visibility of the child widgets."""
        if event.button == 1:
            self.set_expanded(not self.revealer.get_reveal_child())

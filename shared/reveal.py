from gi.repository import Gtk, Gdk
from fabric.widgets.revealer import Revealer
from shared.widget_container import EventBoxWidget


class HoverRevealer(EventBoxWidget):
    """
    A generic widget that shows a visible child (icon/label) and reveals
    a hidden child (box of widgets) on hover or click.
    """

    def __init__(
        self,
        visible_child: Gtk.Widget,
        hidden_child: Gtk.Widget,
        slide_direction: str = "right",
        transition_duration: int = 300,
        expanded_margin: int = 16,
        tooltip: str | None = None,
        **kwargs,
    ):
        super().__init__(tooltip=tooltip or "", **kwargs)

        self.slide_direction = slide_direction
        self.expanded_margin = expanded_margin

        # Setup the animation direction
        gtk_direction = "slide_right" if slide_direction == "right" else "slide_left"

        # Initialize the Fabric Revealer
        self.revealer = Revealer(
            child=hidden_child,
            transition_type=gtk_direction,
            transition_duration=transition_duration,
            reveal_child=False,
        )

        # Add widgets to the internal box based on direction
        # Assuming EventBoxWidget creates self.box (Gtk.Box)
        if slide_direction == "right":
            self.box.add(visible_child)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(visible_child)

        # Initial visibility states
        visible_child.show()
        self.revealer.show()
        self.box.show_all()

        # Connect Events
        self.connect("enter-notify-event", lambda *_: self.set_expanded(True))
        # Capture mouse inside the revealed part so it doesn't close while interacting
        self.revealer.connect("enter-notify-event", lambda *_: self.set_expanded(True))

        self.connect("leave-notify-event", self.on_leave)
        self.revealer.connect("leave-notify-event", self.on_leave)

        self.connect("button-press-event", self.on_click)

    def set_expanded(self, expanded: bool):
        """Reveal or hide child widgets and adjust spacing/margins."""
        margin = self.expanded_margin if expanded else 0

        if self.slide_direction == "right":
            self.revealer.set_margin_start(margin)
            self.revealer.set_margin_end(0)
        else:
            self.revealer.set_margin_start(0)
            self.revealer.set_margin_end(margin)

        self.revealer.set_reveal_child(expanded)

    def on_leave(self, widget, event):
        """Handle mouse leaving the widget area."""
        # Gdk.NotifyType.INFERIOR means the mouse moved to a child window (widget)
        # inside this one, so we shouldn't collapse yet.
        if event.detail == Gdk.NotifyType.INFERIOR:
            return

        self.set_expanded(False)

    def on_click(self, widget, event):
        """Toggle expansion on click."""
        if event.button == 1:
            self.set_expanded(not self.revealer.get_reveal_child())

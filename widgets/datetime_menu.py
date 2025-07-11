from gi.repository import Gtk, GObject
from fabric.widgets.datetime import DateTime
from shared import ButtonWidget
from shared import Popover
import time

class DateTimeWidget(ButtonWidget):
    def __init__(self, config):
        self.dt_config = config["date_time"]
        date_format = self.dt_config.get("format", "%b %d")
        clock_format = self.dt_config.get("clock_format", "24h")

        time_format = "%I:%M %p" if clock_format == "12h" else "%H:%M"
        combined_format = f"{date_format} {time_format}"
        formatters = [combined_format]

        super().__init__(self.dt_config, name="date-time")

        self.datetime = DateTime(
            name="inner-date-time",
            formatters=formatters,
        )
        self.box.children = (self.datetime,)
        self.datetime.show_all()

        self.popup = None
        self.connect("clicked", self.show_popover)

    def do_format(self):
        fmt = self.datetime._formatters[self.datetime._current_index]
        return time.strftime(fmt, time.localtime())

    def show_popover(self, *_):
        if self.popup is None:
            # Create a vertical box container for popover content
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            content_box.set_name("date-menu")  # for styling

            # Create time widget with simpler time format
            clock_format = self.dt_config.get("clock_format", "24h")
            time_fmt = "%I:%M %p" if clock_format == "12h" else "%H:%M"
            time_widget = DateTime(
                formatters=[time_fmt],
                name="popover-time"
            )

            # Create calendar widget
            calendar = Gtk.Calendar()
            calendar.set_name("popover-calendar")

            # Add widgets to container
            content_box.pack_start(time_widget, False, False, 0)
            content_box.pack_start(calendar, True, True, 0)

            content_box.show_all()

            # Create popover pointing to this widget
            self.popup = Popover(
                content=content_box,
                point_to=self,
            )
        self.popup.open()


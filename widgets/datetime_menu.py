from fabric.widgets.datetime import DateTime
from shared import ButtonWidget
from utils.config import widget_config
import time

class DateTimeWidget(ButtonWidget):
    def __init__(self):
        dt_config = widget_config["date_time"]

        date_format = dt_config.get("format", "%b %d")  # e.g. "%b %d"
        clock_format = dt_config.get("clock_format", "24h")

        time_format = "%I:%M %p" if clock_format == "12h" else "%H:%M"
        combined_format = f"{date_format} {time_format}"
        formatters = [combined_format]

        super().__init__(
            widget_config["date_time"],
            name="date-time",
        )

        self.datetime = DateTime(
            name="inner-date-time",
            formatters=formatters,
        )

        self.box.children = (self.datetime,)
        self.datetime.show_all()

    def do_format(self):
        fmt = self.datetime._formatters[self.datetime._current_index]
        return time.strftime(fmt, time.localtime())

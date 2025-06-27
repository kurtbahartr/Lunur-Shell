from fabric.widgets.datetime import DateTime
from utils.config import widget_config
import time

class DateTimeWidget(DateTime):
    def __init__(self):
        dt_config = widget_config["date_time"]

        date_format = dt_config.get("format", "%b %d")  # e.g. "%b %d"
        clock_format = dt_config.get("clock_format", "24h")

        # Time format depends on clock_format
        time_format = "%I:%M %p" if clock_format == "12h" else "%H:%M"

        # Combine date and time formats
        combined_format = f"{date_format} {time_format}"

        # Use just one format string for simplicity
        formatters = [combined_format]

        super().__init__(
            name="date-time",
            formatters=formatters,
        )

    def do_format(self):
        # Override to ensure local time is used correctly
        fmt = self._formatters[self._current_index]
        return time.strftime(fmt, time.localtime())

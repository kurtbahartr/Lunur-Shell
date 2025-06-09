from fabric.widgets.datetime import DateTime
from utils.config import widget_config

class DateTimeWidget(DateTime):
    def __init__(self):
        dt_config = widget_config["date_time"]

        formatters = [
            dt_config.get("format", "%b %-d %H:%M"),
            "%b %-d %H:%M:%S",  # Optional extended format
            "%a %-d %Y"
        ]

        super().__init__(
            name="date-time",
            formatters=formatters,
        )


from gi.repository import Gtk, GLib
from fabric.widgets.datetime import DateTime
from shared.widget_container import ButtonWidget
from shared.pop_over import Popover

import time
import os
from fabric.utils import logger


class DateTimeWidget(ButtonWidget):
    def __init__(self, config):
        self.dt_config = config["date_time"]

        date_format = self.dt_config.get("format", "%b %d")
        clock_format = self.dt_config.get("clock_format", "24h")

        time_format = "%I:%M %p" if clock_format == "12h" else "%H:%M"
        combined_format = f"{date_format} {time_format}"

        super().__init__(self.dt_config, name="date-time")

        self.datetime = DateTime(
            name="inner-date-time",
            formatters=[combined_format],
        )

        self.box.children = (self.datetime,)
        self.datetime.show_all()

        self.popup = None
        self._last_timezone = None  # Defer check to first tick

        self.connect("clicked", self.show_popover)

        GLib.timeout_add_seconds(2, self._check_timezone)

    def _get_timezone(self):
        try:
            # Read symlink directly - much faster than subprocess
            return os.path.realpath("/etc/localtime").split("zoneinfo/")[-1]
        except Exception as e:
            logger.error(f"[datetime] Failed to read timezone: {e}")
            return None

    def _force_refresh(self, widget):
        widget._current_index = widget._current_index
        widget.queue_resize()
        widget.queue_draw()

    def _check_timezone(self):
        tz = self._get_timezone()

        if self._last_timezone is None:
            # First run - just store it
            self._last_timezone = tz
            logger.debug(f"[datetime] Initial timezone: {tz}")
        elif tz and tz != self._last_timezone:
            old = self._last_timezone
            self._last_timezone = tz

            logger.info(f"[datetime] Timezone changed: {old} → {tz}")

            os.environ["TZ"] = tz
            time.tzset()

            self._force_refresh(self.datetime)

            if self.popup:
                self.popup.destroy()
                self.popup = None

        return True

    def show_popover(self, *_):
        if self.popup:
            self.popup.destroy()
            self.popup = None

        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )
        content_box.set_name("date-menu")

        time_date_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        clock_format = self.dt_config.get("clock_format", "24h")
        time_fmt = "%I:%M %p" if clock_format == "12h" else "%H:%M"

        time_widget = DateTime(
            formatters=[time_fmt],
            name="popover-time",
        )

        date_format = self.dt_config.get("format", "%b %d")
        date_fmt = f"{date_format}, %Y"

        date_widget = DateTime(
            formatters=[date_fmt],
            name="popover-date",
        )

        time_date_box.pack_start(time_widget, False, False, 0)
        time_date_box.pack_start(date_widget, False, False, 0)

        calendar_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        calendar_container.set_name("popover-calendar")

        calendar = Gtk.Calendar()
        calendar.set_name("calendar-widget")

        calendar_container.pack_start(calendar, True, True, 0)

        content_box.pack_start(time_date_box, False, False, 0)
        content_box.pack_start(calendar_container, True, True, 0)
        content_box.show_all()

        self.popup = Popover(
            content=content_box,
            point_to=self,
        )
        self.popup.open()

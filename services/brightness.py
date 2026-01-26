import os

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file, logger
from gi.repository import GLib

import utils.functions as helpers


@helpers.run_in_thread
def exec_brightnessctl_async(args: str):
    exec_shell_command_async(f"brightnessctl {args}", lambda _: None)


# Discover screen backlight device
try:
    screen_device_list = os.listdir("/sys/class/backlight")
    screen_device = screen_device_list[0] if screen_device_list else ""
except FileNotFoundError:
    logger.error("No backlight devices found")
    screen_device = ""

# Discover keyboard backlight device
try:
    kbd_list = os.listdir("/sys/class/leds")
    kbd_filtered = [x for x in kbd_list if "kbd_backlight" in x]
    kbd = kbd_filtered[0] if kbd_filtered else ""
except FileNotFoundError:
    logger.error("No keyboard backlight devices found")
    kbd = ""


class Brightness(Service):
    """Service to manage screen brightness levels."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Brightness, cls).__new__(cls)
        return cls._instance

    @Signal
    def brightness_changed(self, percentage: int) -> None:
        """Signal emitted when screen brightness changes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Check if brightnessctl is installed (inside __init__ to avoid module-level exception)
        helpers.check_executable_exists("brightnessctl")

        self.screen_device = screen_device
        self.kbd = kbd

        if self.screen_device == "":
            logger.warning("No screen backlight device detected.")
            self.screen_backlight_path = ""
            self.max_screen = 0
            self.screen_monitor = None
        else:
            self.screen_backlight_path = f"/sys/class/backlight/{self.screen_device}"
            self.max_screen = self._read_max_brightness(self.screen_backlight_path)

            self.screen_monitor = monitor_file(
                f"{self.screen_backlight_path}/brightness"
            )
            self.screen_monitor.connect(
                "changed",
                lambda _, file, *args: self._on_brightness_file_changed(file),
            )

            logger.info(
                f"Brightness service initialized for device: {self.screen_device}"
            )

        self.kbd_backlight_path = f"/sys/class/leds/{self.kbd}" if self.kbd else ""
        self.max_kbd = self._read_max_brightness(self.kbd_backlight_path)

    def _on_brightness_file_changed(self, file):
        """Handle brightness file changes and emit percentage."""
        try:
            raw_value = int(file.load_bytes()[0].get_data())
            if self.max_screen > 0:
                percentage = round((raw_value / self.max_screen) * 100)
                self.emit("brightness_changed", percentage)
        except Exception as e:
            logger.error(f"Error reading brightness file: {e}")

    def _read_max_brightness(self, path: str) -> int:
        max_brightness_path = os.path.join(path, "max_brightness")
        if os.path.exists(max_brightness_path):
            with open(max_brightness_path, "r") as f:
                return int(f.readline())
        return -1

    # Backward compatibility alias
    def do_read_max_brightness(self, path: str) -> int:
        return self._read_max_brightness(path)

    @Property(int, "read-write")
    def screen_brightness(self) -> int:
        """Get raw screen brightness value (0 to max_screen)."""
        if not self.screen_backlight_path:
            logger.warning("Cannot get brightness: no screen device.")
            return -1
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")
        if os.path.exists(brightness_path):
            with open(brightness_path, "r") as f:
                return int(f.readline())
        logger.warning(f"Brightness file does not exist: {brightness_path}")
        return -1

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        """Set raw screen brightness value (0 to max_screen)."""
        if not self.screen_backlight_path:
            logger.warning("Cannot set brightness: no screen device.")
            return
        if not (0 <= value <= self.max_screen):
            value = max(0, min(value, self.max_screen))

        try:
            exec_brightnessctl_async(f"--device '{self.screen_device}' set {value}")
            logger.info(f"Set screen brightness to {value} (out of {self.max_screen})")
            # Note: brightness_changed signal will be emitted by file monitor
        except GLib.Error as e:
            logger.error(f"Error setting screen brightness: {e.message}")
        except Exception as e:
            logger.exception(f"Unexpected error setting screen brightness: {e}")

    @Property(int, "read-write")
    def screen_brightness_percentage(self) -> int:
        """Get screen brightness as percentage (0-100)."""
        if not self.screen_backlight_path or self.max_screen <= 0:
            return 0
        current_brightness = self.screen_brightness
        if current_brightness < 0:
            return 0
        return round((current_brightness / self.max_screen) * 100)

    @screen_brightness_percentage.setter
    def screen_brightness_percentage(self, percentage: int):
        """Set screen brightness as percentage (0-100)."""
        if not self.screen_backlight_path or self.max_screen <= 0:
            logger.warning("Cannot set brightness percentage: no screen device.")
            return

        # Clamp percentage to 0-100
        percentage = max(0, min(percentage, 100))

        # Convert percentage to raw value
        raw_value = round((percentage / 100) * self.max_screen)
        self.screen_brightness = raw_value

    @Property(int, "read-write")
    def keyboard_brightness(self) -> int:  # type: ignore
        """Get raw keyboard brightness value."""
        if not self.kbd_backlight_path:
            logger.warning("No keyboard backlight device detected.")
            return -1
        try:
            with open(self.kbd_backlight_path + "/brightness", "r") as f:
                return int(f.readline())
        except Exception as e:
            logger.exception(f"Failed to read keyboard brightness: {e}")
            return -1

    @keyboard_brightness.setter
    def keyboard_brightness(self, value: int):
        """Set raw keyboard brightness value."""
        if not self.kbd_backlight_path:
            logger.warning("No keyboard backlight device detected.")
            return
        if value < 0 or value > self.max_kbd:
            value = max(0, min(value, self.max_kbd))
        try:
            exec_brightnessctl_async(f"--device '{self.kbd}' set {value}")
        except GLib.Error as e:
            logger.exception(e.message)
        except Exception as e:
            logger.exception(f"Failed to set keyboard brightness: {e}")

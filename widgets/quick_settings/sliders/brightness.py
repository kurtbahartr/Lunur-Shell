from gi.repository import Gtk
from .slider_row import SliderRow
from services.brightness import Brightness
import utils.functions as helpers
from utils.icons import icons
from utils.widget_utils import get_brightness_icon_name


class BrightnessSlider(SliderRow):
    """Brightness slider with automatic service integration."""

    def __init__(self):
        self.brightness_service = Brightness()
        self._updating = False
        self._internal_change = False
        self._signal_id = None
        self._is_realized = False
        self._is_destroyed = False

        # Get initial brightness percent
        try:
            current = self.brightness_service.screen_brightness
            max_brightness = self.brightness_service.max_screen
            initial_percent = helpers.convert_to_percent(current, max_brightness)
        except Exception as e:
            print(f"[BrightnessSlider] Error getting initial brightness: {e}")
            initial_percent = 50

        # Get initial icon
        try:
            icon_info = get_brightness_icon_name(initial_percent)
            initial_icon = icon_info.get("icon", icons["brightness"]["indicator"])
        except Exception:
            initial_icon = icons["brightness"]["indicator"]

        # Initialize parent SliderRow
        super().__init__(
            icon_name=initial_icon,
            min_value=0.1,
            max_value=100,
            initial_value=initial_percent,
            on_change=self._set_brightness,
            style_class="brightness-slider-row",
        )

        # Connect to widget lifecycle signals
        self.connect("realize", self._on_realize)
        self.connect("unrealize", self._on_unrealize)
        self.connect("destroy", self._on_destroy)

    def _on_realize(self, *_):
        """Connect to brightness service when widget is realized."""
        if self._is_destroyed:
            return

        self._is_realized = True

        # Connect to brightness changes
        if self._signal_id is None:
            self._signal_id = self.brightness_service.connect(
                "brightness_changed", self._on_brightness_changed
            )

    def _on_unrealize(self, *_):
        """Disconnect from brightness service when widget is unrealized."""
        self._is_realized = False

    def _on_destroy(self, *_):
        """Cleanup when widget is destroyed."""
        self._is_destroyed = True
        self._is_realized = False

        # Disconnect signal
        if self._signal_id is not None:
            self.brightness_service.disconnect(self._signal_id)
            self._signal_id = None

    def _set_brightness(self, value: float):
        """Set brightness from slider value."""
        if self._updating or self._internal_change or self._is_destroyed:
            return

        try:
            self._updating = True
            max_brightness = self.brightness_service.max_screen
            actual_value = int((value / 100) * max_brightness)
            self.brightness_service.screen_brightness = actual_value
            self._update_icon(value)
        except Exception as e:
            print(f"[BrightnessSlider] Error setting brightness: {e}")
        finally:
            self._updating = False

    def _on_brightness_changed(self, *_):
        """Handle brightness changes from the service."""
        if self._updating or self._is_destroyed or not self._is_realized:
            return

        try:
            self._internal_change = True
            current = self.brightness_service.screen_brightness
            max_brightness = self.brightness_service.max_screen
            percent = helpers.convert_to_percent(current, max_brightness)

            # Only update if we have a valid adjustment
            if self._can_update_value():
                self.set_value(percent)
                self._update_icon(percent)
        except Exception as e:
            print(f"[BrightnessSlider] Error updating from service: {e}")
        finally:
            self._internal_change = False

    def _can_update_value(self) -> bool:
        """Check if it's safe to update the slider value."""
        if self._is_destroyed or not self._is_realized:
            return False

        # Check if adjustment exists and is valid
        if not hasattr(self, "adjustment"):
            return False

        adjustment = getattr(self, "adjustment", None)
        if adjustment is None:
            return False

        # Verify it's a GTK Adjustment
        if not isinstance(adjustment, Gtk.Adjustment):
            return False

        return True

    def set_value(self, value: float):
        """Override set_value with safety checks."""
        if not self._can_update_value():
            return

        try:
            super().set_value(value)
        except Exception as e:
            print(f"[BrightnessSlider] Error in set_value: {e}")

    def _update_icon(self, percent: float):
        """Update the slider icon based on brightness percentage."""
        if self._is_destroyed:
            return

        try:
            icon_info = get_brightness_icon_name(percent)
            icon_name = icon_info.get("icon", icons["brightness"]["indicator"])
            self.set_icon(icon_name)
        except Exception as e:
            print(f"[BrightnessSlider] Error updating icon: {e}")

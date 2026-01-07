# widgets/quick_settings/submenu/bluetooth.py

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from services import bluetooth_service
from shared.buttons import HoverButton
from utils.icons import text_icons
from utils.widget_utils import nerd_font_icon
import utils.functions as helpers


class BluetoothQuickSetting(HoverButton):
    """A button to toggle Bluetooth and display connection status."""

    def __init__(self, **kwargs):
        super().__init__(
            name="quicksettings-togglebutton",
            style_classes=["quicksettings-toggler"],
            **kwargs,
        )

        # Use the existing bluetooth service instance
        self.bluetooth = bluetooth_service

        # Create UI elements
        self.bt_label = Label(
            label="Bluetooth Off",
        )
        self.bt_icon = nerd_font_icon(
            icon=text_icons["bluetooth"]["off"],
            props={"style_classes": ["panel-font-icon"]},
        )

        self.children = Box(
            orientation="h",
            spacing=10,
            children=(
                self.bt_icon,
                self.bt_label,
            ),
        )

        # Connect to bluetooth service signals
        if self.bluetooth:
            self.bluetooth.connect("changed", self.on_bluetooth_changed)

        # Connect click handler
        self.connect("clicked", self.on_click)

        # Initialize state
        self.update_bluetooth_state()

    def on_click(self, *_):
        """Toggle Bluetooth enabled state."""
        if self.bluetooth:
            self.bluetooth.toggle_power()

    def on_bluetooth_changed(self, *_):
        """Handle Bluetooth state changes."""
        self.update_bluetooth_state()

    def update_bluetooth_state(self):
        """Update the widget to reflect current Bluetooth state."""
        if not self.bluetooth:
            self._set_unavailable_state()
            return

        state = self.bluetooth.state

        # Handle adapter not available
        if state in ("absent", "unknown"):
            self._set_unavailable_state()
            return

        # Handle turning on/off states
        if state == "turning-on":
            self._set_turning_on_state()
            return

        if state == "turning-off":
            self._set_turning_off_state()
            return

        if not self.bluetooth.enabled:
            self._set_disabled_state()
            return

        # Bluetooth is enabled, check connection status
        connected_devices = self.bluetooth.connected_devices

        if connected_devices and len(connected_devices) > 0:
            # Get first connected device name
            device = connected_devices[0]
            device_name = getattr(device, "alias", None) or getattr(
                device, "name", "Connected"
            )
            self._set_connected_state(device_name, len(connected_devices))
        else:
            self._set_enabled_not_connected_state()

    def _set_unavailable_state(self):
        """Set UI when Bluetooth is not available."""
        self.bt_label.set_label("No Bluetooth")
        self.bt_icon.set_label(text_icons["bluetooth"]["off"])
        self.remove_style_class("active")

    def _set_disabled_state(self):
        """Set UI for Bluetooth disabled."""
        self.bt_label.set_label("Bluetooth Off")
        self.bt_icon.set_label(text_icons["bluetooth"]["off"])
        self.remove_style_class("active")

    def _set_turning_on_state(self):
        """Set UI for Bluetooth turning on."""
        self.bt_label.set_label("Turning On...")
        self.bt_icon.set_label(text_icons["bluetooth"]["on"])
        self.add_style_class("active")

    def _set_turning_off_state(self):
        """Set UI for Bluetooth turning off."""
        self.bt_label.set_label("Turning Off...")
        self.bt_icon.set_label(text_icons["bluetooth"]["off"])
        self.remove_style_class("active")

    def _set_enabled_not_connected_state(self):
        """Set UI for Bluetooth enabled but not connected."""
        self.bt_label.set_label("Not Connected")
        self.bt_icon.set_label(text_icons["bluetooth"]["on"])
        self.add_style_class("active")

    def _set_connected_state(self, device_name: str, device_count: int = 1):
        """Set UI for Bluetooth connected."""
        if device_count > 1:
            self.bt_label.set_label(
                helpers.truncate(f"{device_name}", 9) + f" +{device_count - 1}"
            )
        else:
            self.bt_label.set_label(helpers.truncate(device_name) or "Connected")
        self.bt_icon.set_label(text_icons["bluetooth"]["connected"])
        self.add_style_class("active")

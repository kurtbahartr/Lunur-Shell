# widgets/quick_settings/submenu/wifi.py

import gi
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow

from shared.buttons import QSChevronButton
from shared.separator import Separator
from shared.submenu import QuickSubMenu
from utils.icons import text_icons
import utils.functions as helpers
from utils.exceptions import NetworkManagerNotFoundError

try:
    from services.network import NetworkService, Wifi
except ImportError:
    raise NetworkManagerNotFoundError()

gi.require_versions({"Gtk": "3.0"})


class WifiSubMenu(QuickSubMenu):
    """A submenu to display WiFi settings."""

    def __init__(self, **kwargs):
        self.network_service = NetworkService()
        self.wifi: Wifi | None = None

        self.separator = Separator(
            orientation="horizontal",
            style_classes=["app-volume-separator"],
        )

        # Content placeholder
        self.child = ScrolledWindow(
            min_content_size=(-1, 190),
            max_content_size=(-1, 190),
            propagate_width=True,
            propagate_height=True,
            child=Box(
                orientation="v",
                children=[
                    self.separator,
                    Box(
                        orientation="v",
                        spacing=10,
                        h_expand=True,
                        children=[
                            Label(
                                label="WiFi Networks",
                                h_align="start",
                                style_classes=["panel-text"],
                            ),
                            Label(
                                label="Scanning coming soon...",
                                h_align="start",
                                style_classes=["submenu-item-label"],
                            ),
                        ],
                    ),
                ],
                spacing=10,
            ),
        )

        super().__init__(
            title="Wi-Fi",
            title_icon=text_icons["wifi"]["strength_4"],  # Static full strength icon
            scan_button=None,
            child=self.child,
            **kwargs,
        )

        self.network_service.connect("device-ready", self._on_device_ready)

        if self.network_service.wifi_device:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _on_device_ready(self, *_):
        if self.network_service.wifi_device and not self.wifi:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _setup_wifi_device(self, wifi_device: Wifi):
        self.wifi = wifi_device
        self.wifi.connect("changed", self._on_wifi_changed)
        self.wifi.connect("notify::enabled", self._on_wifi_enabled_changed)
        self._update_header_state()

    def _on_wifi_changed(self, *_):
        self._update_header_state()

    def _on_wifi_enabled_changed(self, *_):
        self._update_header_state()

    def _update_header_state(self):
        """Update the header label based on connection state."""
        # Safety check for title_label existence
        if not hasattr(self, "title_label"):
            return

        if not self.wifi or not self.wifi.enabled:
            self.title_label.set_label("Wi-Fi")
            return

        if self.wifi.state == "activated" and self.wifi.ssid:
            self.title_label.set_label(helpers.truncate(self.wifi.ssid, max_length=20))
        else:
            self.title_label.set_label("Wi-Fi")


class WifiToggle(QSChevronButton):
    """A widget to display the WiFi status with submenu."""

    def __init__(self, submenu: QuickSubMenu, **kwargs):
        super().__init__(
            style_classes=["quicksettings-toggler"],
            action_label="WiFi Off",
            action_icon=text_icons["wifi"]["disabled"],
            submenu=submenu,
            **kwargs,
        )

        self.network_service = NetworkService()
        self.wifi: Wifi | None = None

        self.network_service.connect("device-ready", self._on_device_ready)

        if self.network_service.wifi_device:
            self._setup_wifi_device(self.network_service.wifi_device)

        self.connect("action-clicked", lambda *_: self._toggle_wifi())

    def _on_device_ready(self, *_):
        if self.network_service.wifi_device and not self.wifi:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _setup_wifi_device(self, wifi_device: Wifi):
        self.wifi = wifi_device
        self.wifi.connect("changed", self._on_wifi_changed)
        self.wifi.connect("notify::enabled", self._on_wifi_enabled_changed)
        self._update_state()

    def _toggle_wifi(self):
        if self.wifi:
            self.wifi.enabled = not self.wifi.enabled

    def _on_wifi_changed(self, *_):
        self._update_state()

    def _on_wifi_enabled_changed(self, *_):
        self._update_state()

    def _update_state(self):
        if not self.wifi:
            self._set_unavailable_state()
            return

        if not self.wifi.enabled:
            self._set_disabled_state()
            return

        ssid = self.wifi.ssid
        strength = self.wifi.strength
        state = self.wifi.state

        if state == "activated" and ssid and ssid != "Disconnected":
            self._set_connected_state(ssid, strength)
        elif state in (
            "prepare",
            "config",
            "need_auth",
            "ip_config",
            "ip_check",
            "secondaries",
        ):
            self._set_connecting_state()
        else:
            self._set_enabled_not_connected_state()

    def _set_unavailable_state(self):
        self.action_label.set_label("No WiFi")
        self.action_icon.set_label(text_icons["wifi"]["generic"])
        self.remove_style_class("active")

    def _set_disabled_state(self):
        self.action_label.set_label("WiFi Off")
        self.action_icon.set_label(text_icons["wifi"]["disabled"])
        self.remove_style_class("active")

    def _set_enabled_not_connected_state(self):
        self.action_label.set_label("Not Connected")
        self.action_icon.set_label(text_icons["wifi"]["disconnected"])
        self.add_style_class("active")

    def _set_connecting_state(self):
        self.action_label.set_label("Connecting...")
        self.action_icon.set_label(text_icons["wifi"]["disconnected"])
        self.add_style_class("active")

    def _set_connected_state(self, ssid: str, strength: int):
        self.action_label.set_label(helpers.truncate(ssid))
        self.action_icon.set_label(self._get_strength_icon(strength))
        self.add_style_class("active")

    def _get_strength_icon(self, strength: int) -> str:
        wifi_icons = text_icons["wifi"]
        if strength >= 80:
            return wifi_icons["strength_4"]
        if strength >= 60:
            return wifi_icons["strength_3"]
        if strength >= 40:
            return wifi_icons["strength_2"]
        if strength >= 20:
            return wifi_icons["strength_1"]
        return wifi_icons["strength_0"]

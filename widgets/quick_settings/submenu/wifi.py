import gi
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import Gtk

from shared.buttons import HoverButton, QSChevronButton, ScanButton
from shared.list import ListBox
from shared.separator import Separator
from shared.submenu import QuickSubMenu
from utils.icons import text_icons, icons
import utils.functions as helpers
from utils.exceptions import NetworkManagerNotFoundError
from utils.widget_utils import nerd_font_icon

try:
    from services.network import NetworkService, Wifi
except ImportError:
    raise NetworkManagerNotFoundError()

gi.require_versions({"Gtk": "3.0"})


class WifiNetworkBox(CenterBox):
    def __init__(self, network: dict, wifi: Wifi, is_active: bool = False, **kwargs):
        super().__init__(
            spacing=2,
            style_classes=["submenu-button"],
            h_expand=True,
            name="wifi-network-box",
            **kwargs,
        )
        self.network = network
        self.wifi = wifi
        self.is_active = is_active
        self.bssid = network.get("bssid", "")
        self.ssid = network.get("ssid", "Unknown")
        self.strength = network.get("strength", 0)
        self.is_secured = network.get("secured", False)

        self.connect_button = HoverButton(style_classes=["submenu-button"])

        if is_active:
            self.connect_button.set_label("Disconnect")
            self.connect_button.connect("clicked", self._on_disconnect_clicked)
        else:
            self.connect_button.set_label("Connect")
            self.connect_button.connect("clicked", self._on_connect_clicked)

        # Get strength icon
        strength_icon = self._get_strength_icon(self.strength)

        network_info_box = Box(
            orientation="h",
            spacing=8,
            h_expand=True,
        )

        network_info_box.add(
            nerd_font_icon(
                icon=strength_icon,
                props={"style_classes": ["panel-font-icon"]},
            )
        )

        if self.is_secured:
            lock_icon = Image(
                icon_name=icons["ui"]["lock"],
                icon_size=16,
                style_classes=["wifi-lock-icon"],
                h_align="start",
                visible=True,
            )
            network_info_box.add(lock_icon)

        network_info_box.add(
            Label(
                label=self.ssid,
                style_classes=["submenu-item-label"],
                ellipsization="end",
                h_expand=True,
                h_align="start",
            )
        )

        self.add_start(network_info_box)
        self.add_end(self.connect_button)

    def _on_connect_clicked(self, *_):
        """Connect to this WiFi network."""
        self.connect_button.set_label("Connecting...")
        network_service = NetworkService()
        network_service.connect_wifi_bssid(self.bssid)

    def _on_disconnect_clicked(self, *_):
        """Disconnect from this WiFi network."""
        self.connect_button.set_label("Disconnecting...")
        self.wifi.disconnect_network()

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


class WifiSubMenu(QuickSubMenu):
    """A submenu to display WiFi settings."""

    def __init__(self, **kwargs):
        self.network_service = NetworkService()
        self.wifi: Wifi | None = None
        self._wifi_signals = []
        self.network_rows = {}

        self.separator = Separator(
            orientation="horizontal",
            style_classes=["app-volume-separator"],
        )

        # Connected network container
        self.connected_network_listbox = ListBox(
            visible=True, name="connected-network-listbox"
        )
        self.connected_network_container = Box(
            orientation="v",
            spacing=10,
            h_expand=True,
            children=[
                Label(
                    label="Connected",
                    h_align="start",
                    style_classes=["panel-text"],
                ),
                self.connected_network_listbox,
            ],
        )

        # Available networks container
        self.available_networks_listbox = ListBox(
            visible=True, name="available-networks-listbox"
        )
        self.available_networks_container = Box(
            orientation="v",
            spacing=4,
            h_expand=True,
            children=[
                Label(
                    label="Available Networks",
                    h_align="start",
                    name="available-networks-label",
                    style_classes=["panel-text"],
                ),
                self.available_networks_listbox,
            ],
        )

        self.scan_button = ScanButton()
        self.scan_button.connect("clicked", self.on_scan_toggle)

        self.child = ScrolledWindow(
            min_content_size=(-1, 190),
            max_content_size=(-1, 190),
            propagate_width=True,
            propagate_height=True,
            child=Box(
                orientation="v",
                children=[
                    self.separator,
                    self.connected_network_container,
                    self.available_networks_container,
                ],
                spacing=10,
            ),
        )

        super().__init__(
            title="Wi-Fi",
            title_icon=text_icons["wifi"]["strength_4"],
            scan_button=self.scan_button,
            child=self.child,
            **kwargs,
        )

        self._device_ready_signal = self.network_service.connect(
            "device-ready", self._on_device_ready
        )
        self.connect("destroy", self._on_destroy)

        if self.network_service.wifi_device:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _on_destroy(self, *_):
        """Clean up signals when widget is destroyed."""
        try:
            self.network_service.disconnect(self._device_ready_signal)
        except Exception:
            pass

        if self.wifi:
            for sig_id in self._wifi_signals:
                try:
                    if self.wifi.handler_is_connected(sig_id):
                        self.wifi.disconnect(sig_id)
                except Exception:
                    pass
        self._wifi_signals.clear()

    def _on_device_ready(self, *_):
        if self.network_service.wifi_device and not self.wifi:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _setup_wifi_device(self, wifi_device: Wifi):
        self.wifi = wifi_device
        self._wifi_signals = [
            self.wifi.connect("changed", self._on_wifi_changed),
            self.wifi.connect("notify::enabled", self._on_wifi_enabled_changed),
            self.wifi.connect("scanning", self._on_scanning_changed),
        ]
        self._update_header_state()
        self._populate_networks()

    def _on_wifi_changed(self, *_):
        self._update_header_state()
        self._populate_networks()

    def _on_wifi_enabled_changed(self, *_):
        self._update_header_state()
        self._populate_networks()

    def _on_scanning_changed(self, wifi, is_scanning: bool):
        """Handle scanning state changes."""
        if is_scanning:
            self.scan_button.add_style_class("active")
        else:
            self.scan_button.remove_style_class("active")

    def on_scan_toggle(self, btn: Button):
        """Start WiFi scanning."""
        if self.wifi and self.wifi.enabled:
            self.wifi.scan()
            self.scan_button.play_animation()

    def _populate_networks(self):
        """Populate the network lists with connected network at top."""
        # Clear existing rows
        for child in self.connected_network_listbox.get_children():
            self.connected_network_listbox.remove(child)
            child.destroy()

        for child in self.available_networks_listbox.get_children():
            self.available_networks_listbox.remove(child)
            child.destroy()

        self.network_rows.clear()

        if not self.wifi or not self.wifi.enabled:
            self.connected_network_container.set_visible(False)
            self.available_networks_container.set_visible(False)
            return

        access_points = self.wifi.access_points
        current_ssid = self.wifi.ssid
        is_connected = self.wifi.state == "activated"

        # Sort by strength (strongest first)
        sorted_aps = sorted(
            access_points, key=lambda x: x.get("strength", 0), reverse=True
        )

        # Track SSIDs we've already added to avoid duplicates
        seen_ssids = set()
        connected_added = False
        available_count = 0

        for ap in sorted_aps:
            ssid = ap.get("ssid", "Unknown")
            if not ssid or ssid == "Unknown" or ssid in seen_ssids:
                continue

            seen_ssids.add(ssid)
            is_active = ssid == current_ssid and is_connected

            network_row = Gtk.ListBoxRow(visible=True, name="wifi-network-row")
            network_box = WifiNetworkBox(ap, self.wifi, is_active=is_active)
            network_row.add(network_box)

            if is_active:
                self.connected_network_listbox.add(network_row)
                connected_added = True
            else:
                self.available_networks_listbox.add(network_row)
                available_count += 1

            self.network_rows[ssid] = (network_row, is_active)

        # Show/hide containers based on content
        self.connected_network_container.set_visible(connected_added)
        self.available_networks_container.set_visible(available_count > 0)

    def _update_header_state(self):
        """Update the header label based on connection state."""
        if not hasattr(self, "title_label"):
            return

        if not self.wifi or not self.wifi.enabled:
            self.title_label.set_label("Wi-Fi")
            return

        if (
            self.wifi.state == "activated"
            and self.wifi.ssid
            and self.wifi.ssid != "Disconnected"
        ):
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
        self._wifi_signals = []

        self._device_ready_signal = self.network_service.connect(
            "device-ready", self._on_device_ready
        )
        self.connect("destroy", self._on_destroy)

        if self.network_service.wifi_device:
            self._setup_wifi_device(self.network_service.wifi_device)

        self.connect("action-clicked", lambda *_: self._toggle_wifi())

    def _on_destroy(self, *_):
        """Clean up signals when widget is destroyed."""
        try:
            self.network_service.disconnect(self._device_ready_signal)
        except Exception:
            pass

        if self.wifi:
            for sig_id in self._wifi_signals:
                try:
                    if self.wifi.handler_is_connected(sig_id):
                        self.wifi.disconnect(sig_id)
                except Exception:
                    pass
        self._wifi_signals.clear()

    def _on_device_ready(self, *_):
        if self.network_service.wifi_device and not self.wifi:
            self._setup_wifi_device(self.network_service.wifi_device)

    def _setup_wifi_device(self, wifi_device: Wifi):
        self.wifi = wifi_device
        self._wifi_signals = [
            self.wifi.connect("changed", self._on_wifi_changed),
            self.wifi.connect("notify::enabled", self._on_wifi_enabled_changed),
        ]
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

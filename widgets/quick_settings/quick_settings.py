from typing import cast
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from utils.widget_settings import BarConfig
from shared.widget_container import ButtonWidget
from services.brightness import Brightness
from utils.exceptions import NetworkManagerNotFoundError
from utils import functions as helpers
from utils.icons import icons
from utils.widget_utils import get_brightness_icon_name
from .services import (
    AudioService,
    BluetoothService,
)
from .quick_settings_menu import QuickSettingsMenu

try:
    from services.network import NetworkService
except ImportError:
    raise NetworkManagerNotFoundError()


class QuickSettings:
    def __init__(self, config, debug=False):
        self.debug = debug
        self.config = config

        # Audio
        self.audio_service = helpers.total_time(
            "Audio Service",
            lambda: self._init_audio(),
            debug=self.debug,
            category="Quick Settings",
        )

        # Network
        self.network_service = helpers.total_time(
            "Network Service",
            lambda: self._init_network(),
            debug=self.debug,
            category="Quick Settings",
        )

        # Brightness
        helpers.total_time(
            "Brightness Service",
            lambda: self._init_brightness(),
            debug=self.debug,
            category="Quick Settings",
        )

        # Bluetooth
        self.bluetooth_service = helpers.total_time(
            "Bluetooth Service",
            lambda: BluetoothService(config),
            debug=self.debug,
            category="Quick Settings",
        )

    def _init_audio(self):
        service = AudioService(self.config)
        service.connect_signals()
        return service

    def _init_network(self):
        # Initialize NetworkService singleton
        network_service = NetworkService()

        # Create UI widgets
        self.show_network_name = self.config.get("show_network_name")
        self.network_icon = Image(style_classes="panel-icon")
        self.network_ssid_label = Label() if self.show_network_name else None

        # Connect signals
        network_service.connect(
            "notify::primary-device", self._on_primary_device_changed
        )
        if network_service.wifi_device:
            network_service.wifi_device.connect("changed", self._on_network_changed)
        if network_service.ethernet_device:
            network_service.ethernet_device.connect("changed", self._on_network_changed)

        # Handle device ready signal for delayed initialization
        network_service.connect("device-ready", self._on_device_ready)

        return network_service

    def _on_device_ready(self, *_):
        """Connect signals when devices are ready"""
        if self.network_service.wifi_device:
            self.network_service.wifi_device.connect(
                "changed", self._on_network_changed
            )
        if self.network_service.ethernet_device:
            self.network_service.ethernet_device.connect(
                "changed", self._on_network_changed
            )
        self.update_network_icon()

    def _on_primary_device_changed(self, *_):
        self.update_network_icon()

    def _on_network_changed(self, *_):
        self.update_network_icon()

    def update_network_icon(self):
        wifi_device = self.network_service.wifi_device
        eth_device = self.network_service.ethernet_device
        icon_name = None
        ssid = None

        if wifi_device and wifi_device.state in ("connected", "activated"):
            icon_name = wifi_device.icon_name
            ssid = wifi_device.ssid if self.show_network_name else None
        elif eth_device and eth_device.internet in ("connected", "activated"):
            icon_name = eth_device.icon_name
            ssid = None
        else:
            icon_name = icons["network"]["wifi"]["disconnected"]

        _update_icon(
            self.network_icon, icon_name, icons["network"]["wifi"]["disconnected"]
        )

        if self.show_network_name and self.network_ssid_label:
            self.network_ssid_label.set_text(helpers.truncate(ssid if ssid else ""))

    def _init_brightness(self):
        self.brightness = Brightness()
        self.show_brightness_percent = self.config.get("show_brightness_percent")
        self.brightness_icon = Image(style_classes="panel-icon")
        self.brightness_percent_label = (
            Label() if self.show_brightness_percent else None
        )

    def connect_brightness_signals(self):
        self.brightness.connect("brightness_changed", self._on_brightness_changed)

    def _on_brightness_changed(self, *_):
        self.update_brightness_icon()

    def update_brightness_icon(self):
        try:
            current_brightness = self.brightness.screen_brightness
            normalized_brightness = int(
                helpers.convert_to_percent(
                    current_brightness, self.brightness.max_screen
                )
            )
            icon_info = get_brightness_icon_name(normalized_brightness)
            icon_name = icon_info.get("icon", icons["brightness"]["indicator"])
        except Exception:
            icon_name = icons["brightness"]["indicator"]
            normalized_brightness = 0

        if icon_name:
            self.brightness_icon.set_from_icon_name(icon_name, 16)
        else:
            self.brightness_icon.set_from_icon_name(
                icons["brightness"]["indicator"], 16
            )

        if self.show_brightness_percent and self.brightness_percent_label:
            self.brightness_percent_label.set_text(f"{normalized_brightness}%")

    def get_icons_and_labels(self, bar_icons):
        icons_map = {
            "audio": self.audio_service.audio_icon,
            "network": self.network_icon,
            "brightness": self.brightness_icon,
            "bluetooth": self.bluetooth_service.bluetooth_icon,
        }
        ordered_icons = []
        for name in bar_icons:
            if name in icons_map:
                ordered_icons.append(icons_map[name])
                if name == "network" and self.network_ssid_label:
                    ordered_icons.append(self.network_ssid_label)
                elif name == "audio" and self.audio_service.audio_percent_label:
                    ordered_icons.append(self.audio_service.audio_percent_label)
                elif name == "brightness" and self.brightness_percent_label:
                    ordered_icons.append(self.brightness_percent_label)
        return ordered_icons

    def update_all_icons(self):
        self.audio_service.update_audio_icon()
        self.update_network_icon()
        self.update_brightness_icon()
        self.bluetooth_service.update_bluetooth_icon()


def _update_icon(
    image_widget: Image, icon_name: str | None, fallback_icon: str, size: int = 16
):
    """Sets the icon on the widget with a fallback if the name is missing."""
    if icon_name:
        image_widget.set_from_icon_name(icon_name, size)
    else:
        image_widget.set_from_icon_name(fallback_icon, size)


class QuickSettingsButtonWidget(ButtonWidget):
    def __init__(self, widget_config: BarConfig, **kwargs):
        # Extract debug flag safely
        self.debug = widget_config.get("general", {}).get("debug", False)

        self.config = cast(dict, widget_config["quick_settings"])
        super().__init__(self.config, name="quick_settings", **kwargs)
        self.popup = None
        self.connect("clicked", self.show_popover)

        # Measure Services Init
        self.services = helpers.total_time(
            "Services Init",
            lambda: QuickSettings(self.config, debug=self.debug),
            debug=self.debug,
            category="Quick Settings",
        )

        bar_icons = self.config.get("bar_icons")

        # UI Generation
        ordered_icons = self.services.get_icons_and_labels(bar_icons)
        self.children = Box(spacing=4, children=ordered_icons)

        # Signal Connections
        self.connect_signals(bar_icons)

        # Initial Updates
        self.update_initial_icons(bar_icons)

    def show_popover(self, *_):
        if self.popup:
            self.popup.destroy()

        # Measure popover open time
        self.popup = helpers.total_time(
            "Popover Open",
            lambda: QuickSettingsMenu(point_to_widget=self, config=self.config),
            debug=self.debug,
            category="Quick Settings",
        )
        self.popup.open()

    def connect_signals(self, bar_icons):
        if "audio" in bar_icons:
            self.services.audio_service.connect_signals()
        if "brightness" in bar_icons:
            self.services.connect_brightness_signals()

    def update_initial_icons(self, bar_icons):
        if "network" in bar_icons:
            self.services.update_network_icon()
        if "audio" in bar_icons:
            self.services.audio_service.update_audio_icon()
        if "brightness" in bar_icons:
            self.services.update_brightness_icon()
        if "bluetooth" in bar_icons:
            self.services.bluetooth_service.update_bluetooth_icon()

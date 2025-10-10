# widgets/quick_settings/quick_settings.py

from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from gi.repository import GLib, Gtk

from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.utils import bulk_connect

import utils.functions as helpers
from services import Brightness, audio_service
from services.network import NetworkService
from services import bluetooth_service
from shared import ButtonWidget, Popover
from utils import BarConfig
from utils.icons import icons
from utils.widget_utils import (
    get_audio_icon_name,
    get_brightness_icon_name,
)

class AudioService:
    def __init__(self, config):
        self.audio = audio_service
        self.show_audio_percent = config.get("show_audio_percent")
        self.audio_icon = Image(style_classes="panel-icon")
        self.audio_percent_label = Label() if self.show_audio_percent else None

    def connect_signals(self):
        self.audio.connect("notify::speaker", self._on_speaker_changed)

    def _on_speaker_changed(self, *_):
        speaker = self.audio.speaker
        if speaker:
            speaker.connect("notify::volume", self._on_volume_changed)
            self.update_audio_icon()

    def _on_volume_changed(self, *_):
        self.update_audio_icon()

    def update_audio_icon(self):
        speaker = self.audio.speaker
        if speaker:
            volume = round(speaker.volume)
            icon_name = get_audio_icon_name(volume, speaker.muted)["icon"]
            self._set_icon(self.audio_icon, icon_name, icons["audio"].get("muted", ""))

            if self.show_audio_percent and self.audio_percent_label:
                self.audio_percent_label.set_text(f"{volume}%")

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str, size: int = 16):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, size)
        else:
            image_widget.set_from_icon_name(fallback_icon, size)

class NetworkServiceWrapper:
    def __init__(self, config):
        self.network = NetworkService()
        self.show_network_name = config.get("show_network_name")
        self.network_icon = Image(style_classes="panel-icon")
        self.network_ssid_label = Label() if self.show_network_name else None

    def connect_signals(self):
        self.network.connect("notify::primary-device", self._on_primary_device_changed)
        self.network.connect("notify::wifi-device", self._on_wifi_device_changed)
        self._connect_network_device_signals()

    def _connect_network_device_signals(self):
        if self.network.wifi_device:
            self.network.wifi_device.connect("notify::signal-strength", self._on_network_device_changed)
            self.network.wifi_device.connect("notify::state", self._on_network_device_changed)

        if self.network.ethernet_device:
            self.network.ethernet_device.connect("notify::state", self._on_network_device_changed)

    def _on_primary_device_changed(self, *_):
        self._connect_network_device_signals()
        self.update_network_icon()

    def _on_wifi_device_changed(self, *_):
        self._connect_network_device_signals()
        self.update_network_icon()

    def _on_network_device_changed(self, *_):
        self.update_network_icon()

    def update_network_icon(self):
        wifi_device = self.network.wifi_device
        eth_device = self.network.ethernet_device
        if wifi_device and getattr(wifi_device, "state", "") in ("connected", "activated"):
            icon_name = wifi_device.get_icon_name()
            ssid = wifi_device.get_ssid() if self.show_network_name else None
        elif eth_device and getattr(eth_device, "state", "") in ("connected", "activated"):
            icon_name = eth_device.get_icon_name()
            ssid = None
        else:
            icon_name = icons["network"]["wifi"]["disconnected"]
            ssid = None

        self._set_icon(self.network_icon, icon_name, icons["network"]["wifi"]["disconnected"])

        if self.show_network_name and self.network_ssid_label:
            self.network_ssid_label.set_text(ssid or "")

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str, size: int = 16):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, size)
        else:
            image_widget.set_from_icon_name(fallback_icon, size)

class BrightnessService:
    def __init__(self, config):
        self.brightness_service = Brightness()
        self.show_brightness_percent = config.get("show_brightness_percent")
        self.brightness_icon = Image(style_classes="panel-icon")
        self.brightness_percent_label = Label() if self.show_brightness_percent else None

    def connect_signals(self):
        self.brightness_service.connect("brightness_changed", self._on_brightness_changed)

    def _on_brightness_changed(self, *_):
        self.update_brightness_icon()

    def update_brightness_icon(self):
        try:
            current_brightness = self.brightness_service.screen_brightness
            normalized_brightness = helpers.convert_to_percent(
                current_brightness, self.brightness_service.max_screen
            )
            icon_info = get_brightness_icon_name(normalized_brightness)
            icon_name = icon_info.get("icon", icons["brightness"]["indicator"])
        except Exception as e:
            print(f"[BrightnessService] Error updating brightness icon: {e}")
            icon_name = icons["brightness"]["indicator"]
            normalized_brightness = 0

        self._set_icon(self.brightness_icon, icon_name, icons["brightness"]["indicator"])

        if self.show_brightness_percent and self.brightness_percent_label:
            self.brightness_percent_label.set_text(f"{normalized_brightness}%")

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str, size: int = 16):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, size)
        else:
            image_widget.set_from_icon_name(fallback_icon, size)

class BluetoothService:
    def __init__(self, config):
        self.bluetooth = bluetooth_service
        self.bluetooth_icon = Image(style_classes="panel-icon")
        self._bluetooth_poll_id = None
        self.connect_signals()

    def connect_signals(self):
        self.bluetooth.connect("notify::enabled", self.update_bluetooth_icon)
        self.bluetooth.connect("device-added", self.update_bluetooth_icon)
        self.bluetooth.connect("device-removed", self.update_bluetooth_icon)
        self.bluetooth.connect("changed", self.update_bluetooth_icon)

    def update_bluetooth_icon(self):
        if not self.bluetooth.enabled:
            icon_name = icons["bluetooth"]["disabled"]
        else:
            icon_name = icons["bluetooth"]["enabled"]

        self._set_icon(self.bluetooth_icon, icon_name, icons["bluetooth"]["disabled"])

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str, size: int = 16):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, size)
        else:
            image_widget.set_from_icon_name(fallback_icon, size)

    def _start_bluetooth_polling(self):
        self._stop_bluetooth_polling()
        self._bluetooth_poll_id = GLib.timeout_add_seconds(5, self.update_bluetooth_icon)

    def _stop_bluetooth_polling(self):
        if self._bluetooth_poll_id is not None:
            GLib.source_remove(self._bluetooth_poll_id)
            self._bluetooth_poll_id = None

class QuickSettings:
    def __init__(self, config):
        self.audio_service = AudioService(config)
        self.network_service = NetworkServiceWrapper(config)
        self.brightness_service = BrightnessService(config)
        self.bluetooth_service = BluetoothService(config)
        
        # Initialize services
        self.audio_service.connect_signals()
        self.network_service.connect_signals()
        self.brightness_service.connect_signals()
        
        # Start Bluetooth polling
        self.bluetooth_service._start_bluetooth_polling()
        
    def update_all_icons(self):
        """Update all icons across services."""
        self.audio_service.update_audio_icon()
        self.network_service.update_network_icon()
        self.brightness_service.update_brightness_icon()
        self.bluetooth_service.update_bluetooth_icon()

class QuickSettings:
    def __init__(self, config):
        self.audio_service = AudioService(config)
        self.network_service = NetworkServiceWrapper(config)
        self.brightness_service = BrightnessService(config)
        self.bluetooth_service = BluetoothService(config)
        
        # Initialize services
        self.audio_service.connect_signals()
        self.network_service.connect_signals()
        self.brightness_service.connect_signals()
        
        # Start Bluetooth polling
        self.bluetooth_service._start_bluetooth_polling()
        
    def get_icons_and_labels(self, bar_icons):
        icons_map = {
            "audio": self.audio_service.audio_icon,
            "network": self.network_service.network_icon,
            "brightness": self.brightness_service.brightness_icon,
            "bluetooth": self.bluetooth_service.bluetooth_icon,
        }

        ordered_icons = []
        for name in bar_icons:
            if name in icons_map:
                ordered_icons.append(icons_map[name])
                if name == "network" and self.network_service.network_ssid_label:
                    ordered_icons.append(self.network_service.network_ssid_label)
                elif name == "audio" and self.audio_service.audio_percent_label:
                    ordered_icons.append(self.audio_service.audio_percent_label)
                elif name == "brightness" and self.brightness_service.brightness_percent_label:
                    ordered_icons.append(self.brightness_service.brightness_percent_label)

        return ordered_icons

    def update_all_icons(self):
        """Update all icons across services."""
        self.audio_service.update_audio_icon()
        self.network_service.update_network_icon()
        self.brightness_service.update_brightness_icon()
        self.bluetooth_service.update_bluetooth_icon()

class QuickSettingsMenu(Popover):
    def __init__(self, point_to_widget, config):
        # Create the main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_name("quick-settings-menu")

        # Add brightness/audio slider
        # Add wifi, bluetooth buttons

        content_box.show_all()

        # Initialize the popover with the content
        super().__init__(
            content=content_box,
            point_to=point_to_widget,
        )

    def populate_menu(self):
        # Future implementation for dynamic menu population
        pass

class QuickSettingsButtonWidget(ButtonWidget):
    def __init__(self, widget_config: BarConfig, **kwargs):
        super().__init__(
            widget_config["quick_settings"], 
            name="quick_settings", 
            **kwargs
        )

        self.popup = None
        self.connect("clicked", self.show_popover)

        self.config = widget_config["quick_settings"]
        self.panel_icon_size = 16

        # Create services and icons handler
        self.services = QuickSettings(self.config)  # Instantiate QuickSettings

        # Prepare bar icons
        bar_icons = self.config.get("bar_icons")

        # Prepare children (icons and labels)
        ordered_icons = self.services.get_icons_and_labels(bar_icons)
        self.children = Box(
            spacing=4,
            children=ordered_icons
        )

        # Connect signals for specified bar icons
        self.connect_signals(bar_icons)

        # Initial icon updates
        self.update_initial_icons(bar_icons)

    def show_popover(self, *_):
        # Destroy existing popup if it exists
        if self.popup:
            self.popup.destroy()
            self.popup = None

        # Create new popover menu
        self.popup = QuickSettingsMenu(
            point_to_widget=self, 
            config=self.config
        )
        self.popup.open()

    def connect_signals(self, bar_icons):
        """Connect all necessary signals for the services"""
        if "audio" in bar_icons:
            self.services.audio_service.connect_signals()

        if "brightness" in bar_icons:
            self.services.brightness_service.connect_signals()

        if "network" in bar_icons:
            self.services.network_service.connect_signals()

        if "bluetooth" in bar_icons:
            self.services.bluetooth_service.connect_signals()
            self.services.bluetooth_service._start_bluetooth_polling()

    def update_initial_icons(self, bar_icons):
        """Update icons initially based on the provided bar icons"""
        if "network" in bar_icons:
            self.services.network_service.update_network_icon()
        if "audio" in bar_icons:
            self.services.audio_service.update_audio_icon()
        if "brightness" in bar_icons:
            self.services.brightness_service.update_brightness_icon()
        if "bluetooth" in bar_icons:
            self.services.bluetooth_service.update_bluetooth_icon()

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(2000, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

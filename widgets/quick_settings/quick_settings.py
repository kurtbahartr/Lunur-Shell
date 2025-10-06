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


class QuickSettingsServices:
    def __init__(self, config):
        # Services
        self.audio = audio_service
        self.network = NetworkService()
        self.brightness_service = Brightness()
        self.bluetooth = bluetooth_service

        # Configuration
        self.config = config
        self.show_network_name = config.get("show_network_name")
        self.show_audio_percent = config.get("show_audio_percent")
        self.show_brightness_percent = config.get("show_brightness_percent")

        # Icon widgets
        self.audio_icon = Image(style_classes="panel-icon")
        self.network_icon = Image(style_classes="panel-icon")
        self.brightness_icon = Image(style_classes="panel-icon")
        self.bluetooth_icon = Image(style_classes="panel-icon")

        # Labels
        self.network_ssid_label = Label() if self.show_network_name else None
        self.audio_percent_label = Label() if self.show_audio_percent else None
        self.brightness_percent_label = Label() if self.show_brightness_percent else None

        # Polling and timeout tracking
        self._timeout_id = None
        self._bluetooth_poll_id = None

    def connect_signals(self, bar_icons):
        """Connect all necessary signals for the services"""
        if "audio" in bar_icons:
            self.audio.connect("notify::speaker", self._on_speaker_changed)

        if "brightness" in bar_icons:
            self.brightness_service.connect("brightness_changed", self._on_brightness_changed)

        if "network" in bar_icons:
            self.network.connect("notify::primary-device", self._on_primary_device_changed)
            self.network.connect("notify::wifi-device", self._on_wifi_device_changed)
            self._connect_network_device_signals()

        if "bluetooth" in bar_icons:
            self.bluetooth.connect("notify::enabled", self._on_bluetooth_enabled_changed)
            self.bluetooth.connect("device-added", self._on_bluetooth_device_changed)
            self.bluetooth.connect("device-removed", self._on_bluetooth_device_changed)
            self.bluetooth.connect("changed", self._on_bluetooth_device_changed)

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
        # Check Ethernet next
        elif eth_device and getattr(eth_device, "state", "") in ("connected", "activated"):
            icon_name = eth_device.get_icon_name()
            ssid = None
        else:
            icon_name = icons["network"]["wifi"]["disconnected"]
            ssid = None

        self._set_icon(
            self.network_icon,
            icon_name,
            fallback_icon=icons["network"]["wifi"]["disconnected"],
        )

        if self.show_network_name and self.network_ssid_label:
            self.network_ssid_label.set_text(ssid or "")

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

            self._set_icon(
                self.audio_icon,
                icon_name,
                fallback_icon=icons["audio"].get("muted", ""),
            )

            if self.show_audio_percent and self.audio_percent_label:
                self.audio_percent_label.set_text(f"{volume}%")

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
            print(f"[QuickSettings] Error updating brightness icon: {e}")
            icon_name = icons["brightness"]["indicator"]
            normalized_brightness = 0

        self._set_icon(
            self.brightness_icon,
            icon_name,
            fallback_icon=icons["brightness"]["indicator"],
        )

        if self.show_brightness_percent and self.brightness_percent_label:
            self.brightness_percent_label.set_text(f"{normalized_brightness}%")

    def _on_bluetooth_enabled_changed(self, *_):
        self.update_bluetooth_icon()

    def _on_bluetooth_device_changed(self, *_):
        self.update_bluetooth_icon()

    def update_bluetooth_icon(self):
        if not self.bluetooth.enabled:
            icon_name = icons["bluetooth"]["disabled"]
        else:
            icon_name = icons["bluetooth"]["enabled"]

        self._set_icon(
            self.bluetooth_icon,
            icon_name,
            fallback_icon=icons["bluetooth"]["disabled"],
        )

    def _start_bluetooth_polling(self):
        self._stop_bluetooth_polling()
        self._bluetooth_poll_id = GLib.timeout_add_seconds(5, self._poll_bluetooth)

    def _stop_bluetooth_polling(self):
        if self._bluetooth_poll_id is not None:
            GLib.source_remove(self._bluetooth_poll_id)
            self._bluetooth_poll_id = None

    def _poll_bluetooth(self):
        self.update_bluetooth_icon()
        return True  # Continue polling

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str, size: int = 16):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, size)
        else:
            print(f"[QuickSettings] Missing icon, using fallback.")
            image_widget.set_from_icon_name(fallback_icon, size)

    def get_icons_and_labels(self, bar_icons):
        icons_map = {
            "audio": self.audio_icon,
            "network": self.network_icon,
            "brightness": self.brightness_icon,
            "bluetooth": self.bluetooth_icon,
        }

        ordered_icons = []
        for name in bar_icons:
            if name in icons_map:
                ordered_icons.append(icons_map[name])
                if name == "network" and self.show_network_name:
                    ordered_icons.append(self.network_ssid_label)
                elif name == "audio" and self.show_audio_percent:
                    ordered_icons.append(self.audio_percent_label)
                elif name == "brightness" and self.show_brightness_percent:
                    ordered_icons.append(self.brightness_percent_label)

        return ordered_icons

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
        self.services = QuickSettingsServices(self.config)

        # Prepare bar icons
        bar_icons = self.config.get("bar_icons")
        
        # Prepare children (icons and labels)
        ordered_icons = self.services.get_icons_and_labels(bar_icons)
        self.children = Box(
            spacing=4,
            children=ordered_icons
        )

        # Connect signals for specified bar icons
        self.services.connect_signals(bar_icons)

        # Initial icon updates
        if "network" in bar_icons:
            self.services.update_network_icon()
        if "audio" in bar_icons:
            self.services.update_audio_icon()
        if "brightness" in bar_icons:
            self.services.update_brightness_icon()
        if "bluetooth" in bar_icons:
            self.services.update_bluetooth_icon()
            self.services._start_bluetooth_polling()

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

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(2000, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None


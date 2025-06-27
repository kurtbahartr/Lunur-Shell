# widgets/quick_settings/quick_settings.py

from fabric.widgets.box import Box
from fabric.widgets.image import Image
from gi.repository import GLib

import utils.functions as helpers
from services import Brightness, audio_service
from services.network import NetworkService
from shared import ButtonWidget
from utils import BarConfig
from utils.icons import icons
from utils.widget_utils import (
    get_audio_icon_name,
    get_brightness_icon_name,
)


class QuickSettingsButtonWidget(ButtonWidget):
    def __init__(self, widget_config: BarConfig, **kwargs):
        super().__init__(
            widget_config["quick_settings"], name="quick_settings", **kwargs
        )

        self.config = widget_config["quick_settings"]
        self.panel_icon_size = 16

        # Services
        self.audio = audio_service
        self.network = NetworkService()
        self.brightness_service = Brightness()

        # Icon widgets
        self.audio_icon = Image(style_classes="panel-icon")
        self.network_icon = Image(style_classes="panel-icon")
        self.brightness_icon = Image(style_classes="panel-icon")

        # Box to hold icons in configured order
        icons_map = {
            "audio": self.audio_icon,
            "network": self.network_icon,
            "brightness": self.brightness_icon,
        }

        bar_icons = self.config.get("bar_icons")
        ordered_icons = [icons_map[name] for name in bar_icons if name in icons_map]

        self.children = Box(children=ordered_icons)

        # Initial updates
        if "network" in bar_icons:
            self.update_network_icon()
        if "audio" in bar_icons:
            self.update_audio_icon()
        if "brightness" in bar_icons:
            self.update_brightness_icon()

        # Connect service signals
        if "audio" in bar_icons:
            self.audio.connect("notify::speaker", self._on_speaker_changed)

        if "brightness" in bar_icons:
            self.brightness_service.connect("brightness_changed", self._on_brightness_changed)

        if "network" in bar_icons:
            self.network.connect("notify::primary-device", self._on_primary_device_changed)
            self.network.connect("notify::wifi-device", self._on_wifi_device_changed)
            self._connect_network_device_signals()

        self._timeout_id = None

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(2000, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

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
        device_type = self.network.primary_device

        if device_type == "wifi" and self.network.wifi_device:
            icon_name = self.network.wifi_device.get_icon_name()
        elif device_type == "ethernet" and self.network.ethernet_device:
            icon_name = self.network.ethernet_device.get_icon_name()
        else:
            icon_name = icons["network"]["wifi"]["disconnected"]

        self._set_icon(
            self.network_icon,
            icon_name,
            fallback_icon=icons["network"]["wifi"]["disconnected"],
        )

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

        self._set_icon(
            self.brightness_icon,
            icon_name,
            fallback_icon=icons["brightness"]["indicator"],
        )

    def _set_icon(self, image_widget: Image, icon_name: str, fallback_icon: str):
        if icon_name:
            image_widget.set_from_icon_name(icon_name, self.panel_icon_size)
        else:
            print(f"[QuickSettings] Missing icon, using fallback.")
            image_widget.set_from_icon_name(fallback_icon, self.panel_icon_size)

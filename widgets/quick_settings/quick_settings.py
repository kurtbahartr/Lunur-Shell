import os
import weakref

from fabric.utils import get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from gi.repository import GLib, Gtk

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

class QuickSettingsButtonBox(Box):
    """A box to display the quick settings buttons."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="v",
            name="quick-settings-button-box",
            spacing=4,
            h_align="start",
            v_align="start",
            v_expand=True,
            **kwargs,
        )

        # Without toggles, just add icons or other widgets directly
        # You can add widgets here if needed, for example network_icon etc.
        # But this class currently does not define self.network_icon etc.

class QuickSettingsButtonWidget(ButtonWidget):
    """A button to display the network, audio, and brightness icons."""

    def __init__(self, widget_config: BarConfig, **kwargs):
        super().__init__(
            widget_config["quick_settings"], name="quick_settings", **kwargs
        )

        self.panel_icon_size = 16
        self.audio = audio_service

        self._timeout_id = None
        self.network = NetworkService()
        self.brightness_service = Brightness()

        # Connect signals
        self.audio.connect("notify::speaker", self.on_speaker_changed)
        self.brightness_service.connect(
            "brightness_changed", self.on_brightness_changed
        )
        self.network.connect("notify::primary-device", self.get_network_icon)

        # Create icon images with proper style
        self.audio_icon = Image(style_classes="panel-icon")
        self.network_icon = Image(style_classes="panel-icon")
        self.brightness_icon = Image(style_classes="panel-icon")

        # Initialize icons
        self.update_brightness()
        self.get_network_icon()
        self.on_speaker_changed()

        self.children = Box(
            children=(
                self.network_icon,
                self.audio_icon,
                self.brightness_icon,
            )
        )

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(2000, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def get_network_icon(self, *_):
        if self.network.primary_device == "wifi":
            wifi = self.network.wifi_device
            if wifi:
                self.network_icon.set_from_icon_name(
                    wifi.get_icon_name(),
                    self.panel_icon_size,
                )
            else:
                self.network_icon.set_from_icon_name(
                    icons["network"]["wifi"]["disconnected"],
                    self.panel_icon_size,
                )
        else:
            ethernet = self.network.ethernet_device
            if ethernet:
                self.network_icon.set_from_icon_name(
                    ethernet.get_icon_name(),
                    self.panel_icon_size,
                )
            else:
                self.network_icon.set_from_icon_name(
                    icons["network"]["wifi"]["disconnected"],
                    self.panel_icon_size,
                )

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return

        self.audio.speaker.connect("notify::volume", self.update_volume)
        self.update_volume()

    def update_volume(self, *_):
        if self.audio.speaker:
            volume = round(self.audio.speaker.volume)
            self.audio_icon.set_from_icon_name(
                get_audio_icon_name(volume, self.audio.speaker.muted)["icon"],
                self.panel_icon_size,
            )

    def on_brightness_changed(self, *_):
        self.update_brightness()

    def update_brightness(self, *_):
        """Update the brightness icon."""
        try:
            # Get the current brightness level
            current_brightness = self.brightness_service.screen_brightness
            normalized_brightness = helpers.convert_to_percent(
                current_brightness,
                self.brightness_service.max_screen,
            )

            # Get the icon information based on the brightness level
            icon_info = get_brightness_icon_name(normalized_brightness)

            if icon_info and "icon" in icon_info:
                icon_name = icon_info["icon"]
                # Log the chosen icon name to help debug
                print(f"Setting brightness icon: {icon_name}")

                # Check if the icon name exists in the icon theme
                if icon_name in icons["brightness"].values():
                    self.brightness_icon.set_from_icon_name(
                        icon_name,
                        self.panel_icon_size,
                    )
                else:
                    print(f"Icon '{icon_name}' not found in icon set, using fallback.")
                    self.brightness_icon.set_from_icon_name(
                        icons["brightness"]["indicator"],
                        self.panel_icon_size,
                    )
            else:
                print("No valid icon info returned by get_brightness_icon_name, using fallback.")
                self.brightness_icon.set_from_icon_name(
                    icons["brightness"]["indicator"],
                    self.panel_icon_size,
                )
        except Exception as e:
            print(f"Error updating brightness icon: {e}")
            self.brightness_icon.set_from_icon_name(
                icons["brightness"]["indicator"],
                self.panel_icon_size,
            )


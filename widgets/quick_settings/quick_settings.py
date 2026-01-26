import time
from fabric.utils import logger
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from utils.widget_settings import BarConfig
from shared.widget_container import ButtonWidget
from services.brightness import Brightness
from utils import functions as helpers
from utils.icons import icons
from utils.widget_utils import get_brightness_icon_name
from .services import (
    AudioService,
    NetworkServiceWrapper,
    BluetoothService,
)
from .quick_settings_menu import QuickSettingsMenu


class QuickSettings:
    def __init__(self, config, debug=False):
        self.debug = debug
        self.config = config

        # Audio
        t_start = time.perf_counter()
        self.audio_service = AudioService(config)
        self.audio_service.connect_signals()
        if self.debug:
            logger.info(
                f"  [QS] Audio Service: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Network
        t_start = time.perf_counter()
        self.network_service = NetworkServiceWrapper(config)
        self.network_service.connect_signals()
        if self.debug:
            logger.info(
                f"  [QS] Network Service: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Brightness - use singleton directly
        t_start = time.perf_counter()
        self.brightness = Brightness()
        self.show_brightness_percent = config.get("show_brightness_percent")
        self.brightness_icon = Image(style_classes="panel-icon")
        self.brightness_percent_label = (
            Label() if self.show_brightness_percent else None
        )
        if self.debug:
            logger.info(
                f"  [QS] Brightness Service: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Bluetooth
        t_start = time.perf_counter()
        self.bluetooth_service = BluetoothService(config)
        self.bluetooth_service._start_bluetooth_polling()
        if self.debug:
            logger.info(
                f"  [QS] Bluetooth Service: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

    def connect_brightness_signals(self):
        self.brightness.connect("brightness_changed", self._on_brightness_changed)

    def _on_brightness_changed(self, *_):
        self.update_brightness_icon()

    def update_brightness_icon(self):
        try:
            current_brightness = self.brightness.screen_brightness
            normalized_brightness = helpers.convert_to_percent(
                current_brightness, self.brightness.max_screen
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
            "network": self.network_service.network_icon,
            "brightness": self.brightness_icon,
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
                elif name == "brightness" and self.brightness_percent_label:
                    ordered_icons.append(self.brightness_percent_label)
        return ordered_icons

    def update_all_icons(self):
        self.audio_service.update_audio_icon()
        self.network_service.update_network_icon()
        self.update_brightness_icon()
        self.bluetooth_service.update_bluetooth_icon()


class QuickSettingsButtonWidget(ButtonWidget):
    def __init__(self, widget_config: BarConfig, **kwargs):
        # Extract debug flag safely
        self.debug = widget_config.get("general", {}).get("debug", False)

        super().__init__(
            widget_config["quick_settings"], name="quick_settings", **kwargs
        )
        self.popup = None
        self.connect("clicked", self.show_popover)

        self.config = widget_config["quick_settings"]

        # Measure Services Init
        t_start = time.perf_counter()
        self.services = QuickSettings(self.config, debug=self.debug)
        if self.debug:
            logger.info(
                f"[QS] Services Init Total: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Measure Icon/Label Generation
        t_start = time.perf_counter()
        bar_icons = self.config.get("bar_icons")
        ordered_icons = self.services.get_icons_and_labels(bar_icons)
        self.children = Box(spacing=4, children=ordered_icons)
        if self.debug:
            logger.info(
                f"[QS] UI Generation: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Measure Signal Connections
        t_start = time.perf_counter()
        self.connect_signals(bar_icons)
        if self.debug:
            logger.info(
                f"[QS] Signal Connections: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

        # Measure Initial Updates
        t_start = time.perf_counter()
        self.update_initial_icons(bar_icons)
        if self.debug:
            logger.info(
                f"[QS] Initial Icon Updates: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

    def show_popover(self, *_):
        if self.popup:
            self.popup.destroy()

        # Optional: Measure popover open time
        t_start = time.perf_counter()
        self.popup = QuickSettingsMenu(point_to_widget=self, config=self.config)
        self.popup.open()
        if self.debug:
            logger.info(
                f"[QS] Popover Open: {(time.perf_counter() - t_start) * 1000:.1f}ms"
            )

    def connect_signals(self, bar_icons):
        if "audio" in bar_icons:
            self.services.audio_service.connect_signals()
        if "brightness" in bar_icons:
            self.services.connect_brightness_signals()
        if "network" in bar_icons:
            self.services.network_service.connect_signals()
        if "bluetooth" in bar_icons:
            self.services.bluetooth_service.connect_signals()
            self.services.bluetooth_service._start_bluetooth_polling()

    def update_initial_icons(self, bar_icons):
        if "network" in bar_icons:
            self.services.network_service.update_network_icon()
        if "audio" in bar_icons:
            self.services.audio_service.update_audio_icon()
        if "brightness" in bar_icons:
            self.services.update_brightness_icon()
        if "bluetooth" in bar_icons:
            self.services.bluetooth_service.update_bluetooth_icon()

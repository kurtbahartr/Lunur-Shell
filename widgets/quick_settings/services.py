# widgets/quick_settings/services.py

from typing import Any, Optional
from gi.repository import GLib
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from services import audio_service, bluetooth_service
from utils.icons import icons
from utils.widget_utils import get_audio_icon_name


def _update_icon(
    image_widget: Image, icon_name: Optional[str], fallback_icon: str, size: int = 16
):
    """Sets the icon on the widget with a fallback if the name is missing."""
    if icon_name:
        image_widget.set_from_icon_name(icon_name, size)
    else:
        image_widget.set_from_icon_name(fallback_icon, size)


class AudioService:
    def __init__(self, config: Any):
        self.audio = audio_service
        self.show_audio_percent = config.get("show_audio_percent")
        self.audio_icon = Image(style_classes="panel-icon")

        # Instantiate directly using the top-level import
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
            icon_info = get_audio_icon_name(int(volume), speaker.muted)
            icon_name = str(icon_info.get("icon", icons["audio"].get("muted", "")))

            _update_icon(self.audio_icon, icon_name, icons["audio"].get("muted", ""))

            if self.show_audio_percent and self.audio_percent_label:
                self.audio_percent_label.set_text(f"{volume}%")


class BluetoothService:
    DEVICE_ICON_MAP = {
        "headphones": icons["audio"]["type"]["headset"],
        "headset": icons["audio"]["type"]["headset"],
        "speaker": icons["audio"]["type"]["speaker"],
    }

    def __init__(self, config: Any):
        self.bluetooth = bluetooth_service
        self.bluetooth_icon = Image(style_classes="panel-icon")
        self._bluetooth_poll_id = None
        self.connect_signals()

    def connect_signals(self):
        self.bluetooth.connect("notify::enabled", self.update_bluetooth_icon)
        self.bluetooth.connect("device-added", self.update_bluetooth_icon)
        self.bluetooth.connect("device-removed", self.update_bluetooth_icon)
        self.bluetooth.connect("changed", self.update_bluetooth_icon)

    def update_bluetooth_icon(self, *_):
        if not self.bluetooth.enabled:
            icon_name = icons["bluetooth"]["disabled"]
        else:
            icon_name = icons["bluetooth"]["enabled"]
            for device in self.bluetooth.get_connected_devices():
                dev_type = getattr(device, "type", "").lower()
                if dev_type in self.DEVICE_ICON_MAP:
                    icon_name = self.DEVICE_ICON_MAP[dev_type]
                    break

        _update_icon(self.bluetooth_icon, icon_name, icons["bluetooth"]["disabled"])

    def _start_bluetooth_polling(self):
        self._stop_bluetooth_polling()
        self._bluetooth_poll_id = GLib.timeout_add_seconds(
            5, self.update_bluetooth_icon
        )

    def _stop_bluetooth_polling(self):
        if self._bluetooth_poll_id is not None:
            GLib.source_remove(self._bluetooth_poll_id)
            self._bluetooth_poll_id = None

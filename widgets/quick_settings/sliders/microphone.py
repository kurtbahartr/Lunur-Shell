# widgets/quick_settings/sliders/microphone.py

from .slider_row import SliderRow
from services import audio_service
from utils.icons import icons


def get_mic_icon_name(volume: float, muted: bool = False) -> str:
    """Get the appropriate microphone icon based on volume and mute state."""
    if muted:
        return icons["audio"]["mic"]["muted"]

    if volume == 0:
        return icons["audio"]["mic"]["muted"]
    elif volume < 33:
        return icons["audio"]["mic"]["low"]
    elif volume < 66:
        return icons["audio"]["mic"]["medium"]
    else:
        return icons["audio"]["mic"]["high"]


class MicrophoneSlider(SliderRow):
    """Microphone slider with automatic service integration."""

    def __init__(self):
        self.audio = audio_service

        # Get initial volume
        initial_volume = 50
        if self.audio.microphone:
            initial_volume = round(self.audio.microphone.volume)

        super().__init__(
            icon_name=icons["audio"]["mic"]["medium"],
            min_value=0,
            max_value=100,
            initial_value=initial_volume,
            on_change=self._set_volume,
            style_class="microphone-slider-row",
        )

        # Connect to audio changes
        self.audio.connect("notify::microphone", self._on_microphone_changed)
        if self.audio.microphone:
            self._connect_microphone_signals()

        self._update_icon(initial_volume)

    def _connect_microphone_signals(self):
        if self.audio.microphone:
            self.audio.microphone.connect("notify::volume", self._on_volume_changed)
            self.audio.microphone.connect("notify::muted", self._on_volume_changed)

    def _on_microphone_changed(self, *_):
        self._connect_microphone_signals()
        self._on_volume_changed()

    def _set_volume(self, value: float):
        if self.audio.microphone:
            self.audio.microphone.volume = value

    def _on_volume_changed(self, *_):
        if self.audio.microphone:
            volume = round(self.audio.microphone.volume)
            muted = self.audio.microphone.muted
            self.set_value(volume)
            self._update_icon(volume, muted)

    def _update_icon(self, volume: float, muted: bool = False):
        try:
            icon_name = get_mic_icon_name(volume, muted)
            self.set_icon(icon_name)
        except Exception:
            pass

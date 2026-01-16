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

        self._mic_signal_ids = []
        self._audio_signal_id = None

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
        self._audio_signal_id = self.audio.connect(
            "notify::microphone", self._on_microphone_changed
        )

        self._connect_microphone_signals()
        self._update_icon(initial_volume)

        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *args):
        """Disconnect all signals to prevent errors when widget is removed."""
        # Disconnect global audio service signal
        if self._audio_signal_id:
            self.audio.disconnect(self._audio_signal_id)
            self._audio_signal_id = None

        # Disconnect specific microphone signals
        self._disconnect_mic_signals()

    def _disconnect_mic_signals(self):
        """Disconnects signals from the previously tracked microphone object."""
        for mic_obj, handler_id in self._mic_signal_ids:
            try:
                if mic_obj.handler_is_connected(handler_id):
                    mic_obj.disconnect(handler_id)
            except Exception:
                # Object might already be finalized
                pass
        self._mic_signal_ids.clear()

    def _connect_microphone_signals(self):
        # First, remove old connections to prevent duplicates or memory leaks
        self._disconnect_mic_signals()

        if self.audio.microphone:
            mic = self.audio.microphone
            # Store the object AND the ID so we can disconnect specifically from this object later
            self._mic_signal_ids.append(
                (mic, mic.connect("notify::volume", self._on_volume_changed))
            )
            self._mic_signal_ids.append(
                (mic, mic.connect("notify::muted", self._on_volume_changed))
            )

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

            # Defensive check: ensure widget is still valid before updating UI
            try:
                self.set_value(volume)
                self._update_icon(volume, muted)
            except Exception:
                pass

    def _update_icon(self, volume: float, muted: bool = False):
        try:
            icon_name = get_mic_icon_name(volume, muted)
            self.set_icon(icon_name)
        except Exception:
            pass

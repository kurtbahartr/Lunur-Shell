from typing import Optional
from fabric.utils import get_relative_path

from services.screen_record import ScreenRecorderService
from shared.widget_container import ButtonWidget
from utils.icons import text_icons
from utils.widget_utils import nerd_font_icon


class RecorderWidget(ButtonWidget):
    """A widget to record the system"""

    def __init__(self, config=None, **kwargs):
        # Extract recorder specific config from the main config
        if config is None:
            recorder_config = {}
        elif isinstance(config, dict) and "recorder" in config:
            recorder_config = config.get("recorder", {})
        else:
            # Assume it's already the recorder config section
            recorder_config = config

        super().__init__(config=recorder_config, name="recorder", **kwargs)

        # Initial UI setup
        self.recording_idle_image = nerd_font_icon(
            icon=text_icons.get("recorder", "󰑊"),
            props={"style_classes": "panel-font-icon"},
        )
        self.box.add(self.recording_idle_image)

        if self.config.get("tooltip"):
            self.set_tooltip_text("Recording stopped")

        self.recorder_service: Optional[ScreenRecorderService] = None

        self.connect("clicked", self.handle_click)

        # Internal state
        self._recording_lottie = None
        self.initialized = False

    def lazy_init(self):
        """Initialize the recorder service if not already initialized."""
        if not self.initialized:
            self.recorder_service = ScreenRecorderService()
            self.recorder_service.connect("recording", self.update_ui)
            self.initialized = True

    @property
    def recording_ongoing_lottie(self):
        from shared.lottie import LottieAnimation, LottieAnimationWidget

        if self._recording_lottie is None:
            self._recording_lottie = LottieAnimationWidget(
                LottieAnimation.from_file(
                    f"{get_relative_path('../assets/icons/')}/recording.json",
                ),
                scale=0.30,
                h_align="center",
                v_align="center",
            )
        return self._recording_lottie

    def handle_click(self, *_):
        """Start or stop recording the screen."""
        self.lazy_init()

        if not self.initialized or self.recorder_service is None:
            return  # Early exit if service not available

        if self.recorder_service.is_recording:
            self.recorder_service.screenrecord_stop()
        else:
            self.recorder_service.screenrecord_start(config=self.config)

    def update_ui(self, _, is_recording: bool):
        current_children = self.box.get_children()

        if is_recording:
            if self.recording_idle_image in current_children:
                self.box.remove(self.recording_idle_image)
                self.box.add(self.recording_ongoing_lottie)

            self.recording_ongoing_lottie.play_loop()

            if self.config.get("tooltip"):
                self.set_tooltip_text("Recording started")
        else:
            if (
                self._recording_lottie
                and self.recording_ongoing_lottie in current_children
            ):
                self.box.remove(self.recording_ongoing_lottie)
                self.box.add(self.recording_idle_image)

                self.recording_ongoing_lottie.stop_play()

            if self.config.get("tooltip"):
                self.set_tooltip_text("Recording stopped")

from typing import ClassVar
import gi
from fabric.utils import bulk_connect, remove_handler
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from gi.repository import GLib, GObject

from services import audio_service
from utils.icons import icons
from utils.widget_utils import create_scale, get_audio_icon_name

gi.require_versions({"GObject": "2.0"})


class GenericOSDContainer(Box):
    """Generic OSD container for audio."""

    def __init__(self, config: dict, **kwargs):
        is_vertical = config["orientation"] == "vertical"

        super().__init__(
            orientation=config["orientation"],
            spacing=10,
            name="osd-container",
            style_classes="vertical" if is_vertical else "",
            **kwargs,
        )

        self.icon_size = config["icon_size"]
        self.icon = Image(
            icon_name=icons["audio"]["volume"]["medium"],
            icon_size=self.icon_size,
        )

        scale_style = "scale {min-height: 150px; min-width: 11px;}" if is_vertical else ""

        self.scale = create_scale(
            name="osd-scale",
            orientation=config["orientation"],
            h_expand=is_vertical,
            v_expand=is_vertical,
            duration=config["transition_duration"] / 1000,  # seconds
            curve=(0.34, 1.56, 0.64, 1.0),
            inverted=is_vertical,
            style=scale_style,
        )

        self.children = (self.icon, self.scale)

        self.show_level = config["percentage"]
        if self.show_level:
            self.level = Label(name="osd-level", h_align="center", h_expand=True)
            self.add(self.level)

    def update_values(self, value):
        round_value = round(value)
        self.scale.set_value(round_value)
        if self.show_level:
            self.level.set_label(f"{round_value}%")

class AudioOSDContainer(GenericOSDContainer):
    """OSD container for audio volume."""

    __gsignals__: ClassVar = {
        "volume-changed": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, config: dict, **kwargs):
        super().__init__(config=config, **kwargs)
        self.audio_service = audio_service
        self.previous_volume = None
        self.previous_muted = None

        bulk_connect(
            self.audio_service,
            {
                "notify::speaker": self.on_speaker_changed,
                "changed": self.check_mute,
            },
        )

    def check_mute(self, *_):
        if not self.audio_service.speaker:
            return

        current_muted = self.audio_service.speaker.muted
        if self.previous_muted is None or current_muted != self.previous_muted:
            self.previous_muted = current_muted
            self.update_icon()
            if current_muted:
                self.scale.add_style_class("muted")
            else:
                self.scale.remove_style_class("muted")
            self.emit("volume-changed")

    def on_speaker_changed(self, *_):
        if speaker := self.audio_service.speaker:
            speaker.connect("notify::volume", self.update_volume)

    def update_volume(self, speaker, *_):
        if not self.audio_service.speaker:
            return

        speaker.handler_block_by_func(self.update_volume)
        volume = round(self.audio_service.speaker.volume)

        if self.previous_volume is None or volume != self.previous_volume:
            is_over_amplified = volume > 100
            self.previous_volume = volume

            if is_over_amplified:
                self.scale.add_style_class("overamplified")
            else:
                self.scale.remove_style_class("overamplified")

            if self.audio_service.speaker.muted or volume == 0:
                self.update_icon()
                self.scale.add_style_class("muted")
            else:
                self.scale.remove_style_class("muted")
                self.update_icon(volume)

            self.update_values(volume)
            self.emit("volume-changed")

        speaker.handler_unblock_by_func(self.update_volume)

    def update_icon(self, volume=0):
        icon_name = get_audio_icon_name(volume, self.audio_service.speaker.muted)["icon"]
        self.icon.set_from_icon_name(icon_name, self.icon_size)

class OSDWindow(Window):
    """Top-level OSD window for audio with anchor support."""

    def __init__(self, config: dict, **kwargs):
        self.hide_timer_id = None
        self.config = config["osd"]

        self.audio_container = AudioOSDContainer(config=self.config)
        self.audio_container.connect("volume-changed", self.show_audio)

        self.timeout = self.config["timeout"]

        self.revealer = Revealer(
            name="osd-revealer",
            transition_type=self.config["transition_type"],
            transition_duration=self.config["transition_duration"],
            child_revealed=False,
        )

        anchor_string = self.config["anchor"]

        super().__init__(
            layer="overlay",
            anchor=anchor_string,
            child=self.revealer,
            visible=False,
            pass_through=True,
            name="osd",
            **kwargs,
        )

    def show_audio(self, *_):
        if self.revealer.get_child() != self.audio_container:
            if self.revealer.get_child():
                self.revealer.remove(self.revealer.get_child())
            self.revealer.add(self.audio_container)

        self.set_visible(True)

        if self.hide_timer_id is not None:
            remove_handler(self.hide_timer_id)
            self.hide_timer_id = None

        GLib.idle_add(lambda: self.revealer.set_reveal_child(True))
        self.hide_timer_id = GLib.timeout_add(self.timeout, self._hide)

    def _hide(self):
        self.revealer.set_reveal_child(False)
        GLib.timeout_add(self.revealer.get_transition_duration(), self._finalize_hide)
        return False

    def _finalize_hide(self):
        self.set_visible(False)
        self.hide_timer_id = None
        return False

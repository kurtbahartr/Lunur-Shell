import re
from gi.repository import GObject, GLib
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from loguru import logger

from services.mpris import MprisPlayer, MprisPlayerManager
from shared.widget_container import ButtonWidget
from utils.icons import icons
from utils.widget_utils import get_icon
from utils import BarConfig


class MprisWidget(ButtonWidget):
    """A widget to control the MPRIS, showing a music icon and current track label.
    The label is hidden by default and revealed on hover."""

    POLL_INTERVAL_MS = 2000  # poll every 2 seconds

    def __init__(self, widget_config=None, **kwargs):
        if widget_config is None:
            widget_config = BarConfig()

        config = widget_config["mpris"] if "mpris" in widget_config else widget_config
        super().__init__(config=config, name="mpris", **kwargs)

        self.player = None
        self.mpris_manager = MprisPlayerManager()

        icon_name = icons["mpris"]["music"]
        self.icon_widget = get_icon(icon_name, size=self.config.get("icon_size"))

        self.label = Label(label="", style_classes="panel-text")

        self.revealer = Revealer(
            child=self.label,
            transition_duration=self.config.get("transition_duration"),
            transition_type="slide_right",
            reveal_child=False,
        )

        self.box.set_spacing(4)
        self.box.add(self.icon_widget)
        self.box.add(self.revealer)

        self.icon_widget.show()
        self.label.show()
        self.box.show_all()

        self._set_player_from_manager()

        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_players)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

    def _poll_players(self):
        current_players = self.mpris_manager.players
        if not current_players and self.player is not None:
            logger.info("[MPRIS] No players detected during poll, clearing player.")
            self._clear_player()
        elif current_players:
            if not self.player or self.player._player not in current_players:
                logger.info("[MPRIS] New player detected during poll, updating player.")
                self._set_player(MprisPlayer(current_players[0]))
        return True

    def _set_player_from_manager(self):
        players = self.mpris_manager.players
        if players:
            self._set_player(MprisPlayer(players[0]))
        else:
            self._clear_player()

    def _set_player(self, player):
        if self.player:
            self.player.disconnect_by_func(self.on_metadata_update)

        self.player = player

        self.player.bind_property(
            "title",
            self.label,
            "label",
            GObject.BindingFlags.DEFAULT,
            lambda _, x: re.sub(r"\r?\n", " ", x) if x not in ("", None) else "",
        )

        self.player.connect("notify::metadata", self.on_metadata_update)

        title = self.player.title or ""
        self.label.set_text(title)
        if self.config.get("tooltip"):
            self.set_tooltip_text(title)

    def _clear_player(self):
        self.player = None
        self.label.set_text("")
        if self.config.get("tooltip"):
            self.set_tooltip_text("")

    def on_metadata_update(self, *_):
        if not self.player:
            return

        current_title = self.player.title or ""
        logger.info(f"[MPRIS] Metadata updated, new title: {current_title}")

        self.label.set_text(current_title)
        if self.config.get("tooltip"):
            self.set_tooltip_text(current_title)

    def on_mouse_enter(self, *_):
        self.revealer.set_reveal_child(True)

    def on_mouse_leave(self, *_):
        self.revealer.set_reveal_child(False)

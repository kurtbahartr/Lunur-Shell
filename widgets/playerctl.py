import re
from gi.repository import GObject, GLib, Playerctl
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer

from shared.widget_container import ButtonWidget
from utils.icons import icons
from utils.widget_utils import get_icon
from utils import BarConfig


class PlayerctlWidget(ButtonWidget):
    """A widget to control media playback using Playerctl, showing a music icon and current track label.
    The label is hidden by default and revealed on hover."""

    POLL_INTERVAL_MS = 2000  # poll every 2 seconds

    def __init__(self, widget_config=None, **kwargs):
        if widget_config is None:
            widget_config = BarConfig()

        config = widget_config["playerctl"] if "playerctl" in widget_config else widget_config
        super().__init__(config=config, name="playerctl", **kwargs)

        self.player = None
        self.player_manager = Playerctl.PlayerManager.new()

        icon_name = icons["playerctl"]["music"]
        self.icon_widget = get_icon(icon_name, size=self.config.get("icon_size"))
        self.label = Label(label="", style_classes="panel-text")

        # Require explicit valid slide_direction: "left" or "right"
        direction = self.config.get("slide_direction")
        if direction == "left":
            gtk_direction = "slide_left"
        elif direction == "right":
            gtk_direction = "slide_right"
        else:
            raise ValueError(
                f"[PLAYERCTL] Invalid or missing 'slide_direction'. Expected 'left' or 'right', got '{direction}'"
            )

        self.revealer = Revealer(
            child=self.label,
            transition_duration=self.config.get("transition_duration"),
            transition_type=gtk_direction,
            reveal_child=False,
        )

        if direction == "right":
            self.box.add(self.icon_widget)    # Icon on the left
            self.box.add(self.revealer)       # Label on the right
        else:
            self.box.add(self.revealer)       # Label on the left
            self.box.add(self.icon_widget)    # Icon on the right

        self.icon_widget.show()
        self.label.show()
        self.box.show_all()

        # Setup Playerctl player manager
        self.player_manager.connect("player-vanished", self._on_player_vanished)
        self.player_manager.connect("name-appeared", self._on_player_appeared)

        # Initial player setup
        self._setup_initial_player()

        # Periodic check for players
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_players)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

    def _setup_initial_player(self):
        """Set up the initial player if any are available."""
        player_names = self.player_manager.props.player_names
        if player_names:
            first_player_name = player_names[0]
            player = Playerctl.Player.new_from_name(first_player_name)
            self._set_player(player)

    def _poll_players(self):
        """Periodically check for available players."""
        player_names = self.player_manager.props.player_names
        if not player_names and self.player:
            self._clear_player()
        elif player_names:
            if not self.player or self.player.props.player_name not in [p.name for p in player_names]:
                first_player_name = player_names[0]
                player = Playerctl.Player.new_from_name(first_player_name)
                self._set_player(player)
        return True

    def _on_player_vanished(self, _, player):
        """Handle player disappearing."""
        if self.player and player.props.player_name == self.player.props.player_name:
            self._clear_player()

    def _on_player_appeared(self, _, player_name):
        """Handle new player appearing."""
        if not self.player:
            player = Playerctl.Player.new_from_name(player_name)
            self._set_player(player)

    def _set_player(self, player):
        """Set up a new player and connect signals."""
        # Disconnect previous player signals if exists
        if self.player:
            # Disconnect any existing signal handlers
            try:
                self.player.disconnect_by_func(self._on_metadata_changed)
            except TypeError:
                pass

        self.player = player

        # Connect metadata and playback status signals
        player.connect("metadata", self._on_metadata_changed)
        
        # Update initial metadata
        self._on_metadata_changed(player, None)

    def _on_metadata_changed(self, player, metadata=None):
        """Update widget when metadata changes."""
        if not self.player:
            return

        # Get title, using empty string if not available
        title = player.get_title() or ""
        
        # Clean up title (remove newlines)
        title = re.sub(r"\r?\n", " ", title)
        
        # Update label
        self.label.set_text(title)
        
        # Update tooltip if configured
        if self.config.get("tooltip"):
            self.set_tooltip_text(title)

    def _clear_player(self):
        """Clear the current player."""
        self.player = None
        self.label.set_text("")
        if self.config.get("tooltip"):
            self.set_tooltip_text("")

    def on_mouse_enter(self, *_):
        """Show label when mouse enters."""
        self.revealer.set_reveal_child(True)
        self.box.set_spacing(4)

    def on_mouse_leave(self, *_):
        """Hide label when mouse leaves."""
        self.revealer.set_reveal_child(False)
        self.box.set_spacing(4)
        

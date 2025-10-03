import re
from gi.repository import GObject, GLib, Playerctl
from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.image import Image

from shared.widget_container import EventBoxWidget
from utils.icons import icons
from utils import BarConfig
from widgets.common.resolver import create_slide_revealer, resolve_icon

class PlayerctlWidget(EventBoxWidget):
    """A widget to control media playback using Playerctl, showing a music icon and current track label."""

    POLL_INTERVAL_MS = 2000  # poll every 2 seconds

    def __init__(self, widget_config=None, **kwargs):
        if widget_config is None:
            widget_config = BarConfig()

        config = widget_config["playerctl"] if "playerctl" in widget_config else widget_config
        super().__init__(**kwargs)

        self.config = config
        self.player = None
        self.player_manager = Playerctl.PlayerManager.new()

        # Config options
        self.icon_size = self.config.get("icon_size", 16)
        self.slide_direction = self.config.get("slide_direction", "left")
        self.transition_duration = self.config.get("transition_duration", 250)
        self.tooltip_enabled = self.config.get("tooltip", True)

        # Music icon
        icon_name = icons["playerctl"]["music"]
        self.icon_widget = Image(
            icon_name=icon_name, 
            icon_size=self.icon_size, 
            style_classes=["panel-icon"]
        )

        # Label for track information
        self.label = Label(label="", style_classes="panel-text")

        # Create revealer for the label
        self.revealer = create_slide_revealer(
            child=self.label,
            slide_direction=self.slide_direction,
            transition_duration=self.transition_duration,
            initially_revealed=False
        )

        # Layout based on slide direction
        if self.slide_direction == "right":
            self.box.add(self.icon_widget)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(self.icon_widget)

        self.icon_widget.show()
        self.label.show()
        self.box.show_all()

        # Player manager setup
        self.player_manager.connect("player-vanished", self._on_player_vanished)
        self.player_manager.connect("name-appeared", self._on_player_appeared)

        # Initial player setup
        self._setup_initial_player()

        # Periodic player check
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_players)

        # Hover events
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

        # Get title and artist
        title = player.get_title() or ""
        artist = player.get_artist() or ""

        # Clean up text (remove newlines)
        title = re.sub(r"\r?\n", " ", title)
        artist = re.sub(r"\r?\n", " ", artist)

        # Combine title and artist
        if artist:
            display_text = f"{title} – {artist}"
        else:
            display_text = title

        # Update label
        self.label.set_text(display_text)

        # Update tooltip if configured
        if self.tooltip_enabled:
            self.set_tooltip_text(display_text)

    def _clear_player(self):
        """Clear the current player."""
        self.player = None
        self.label.set_text("")
        if self.tooltip_enabled:
            self.set_tooltip_text("")

    def on_mouse_enter(self, *_):
        """Show label when mouse enters."""
        self.revealer.set_reveal_child(True)
        self.box.set_spacing(4)

    def on_mouse_leave(self, widget, event):
        """Hide label when mouse leaves, similar to SystemTrayWidget."""
        allocation = self.revealer.get_allocation()
        x, y = widget.translate_coordinates(self.revealer, int(event.x), int(event.y))
        
        if not (0 <= x <= allocation.width and 0 <= y <= allocation.height):
            self.revealer.set_reveal_child(False)
            self.box.set_spacing(4)


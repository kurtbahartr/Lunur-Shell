import gi

from gi.repository import GObject, GLib
from utils.exceptions import PlayerctlImportError

try:
    gi.require_version("Playerctl", "2.0")
    from gi.repository import Playerctl
except ValueError:
    raise PlayerctlImportError()


class PlayerctlService(GObject.Object):
    __gsignals__ = {
        "metadata-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "player-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "status-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        super().__init__()

        self._current_player_name = None
        self._cached_metadata = {}
        self._player_valid = False
        self._players = {}  # name_str -> player
        self._destroyed = False

        # Player manager setup
        self.player_manager = Playerctl.PlayerManager.new()

        # Connect manager signals
        self.player_manager.connect("player-vanished", self._on_player_vanished)
        self.player_manager.connect("name-appeared", self._on_name_appeared)

        # Initialize with existing players
        for player_name in self.player_manager.props.player_names:
            GLib.idle_add(self._init_player, player_name)

    def destroy(self):
        self._destroyed = True
        self._player_valid = False
        self._players.clear()

    @property
    def is_valid(self):
        return self._player_valid and not self._destroyed

    def _init_player(self, player_name):
        """Initialize a player - called via idle_add to defer from signal context."""
        if self._destroyed:
            return False
        if not isinstance(player_name, Playerctl.PlayerName):
            return False

        name_str = player_name.name
        if name_str in self._players:
            return False

        try:
            player = Playerctl.Player.new_from_name(player_name)
            self.player_manager.manage_player(player)
            self._players[name_str] = player

            # Connect signals - but defer actual property access
            player.connect("metadata", self._on_metadata_signal)
            player.connect("playback-status", self._on_status_signal)

            # If no active player, use this one
            if not self._current_player_name:
                self._current_player_name = name_str
                self._player_valid = True
                # Defer metadata fetch
                GLib.idle_add(self._fetch_metadata)
                self.emit("player-changed")

        except Exception as e:
            print(f"Error initializing player {name_str}: {e}")

        return False

    def _on_name_appeared(self, manager, player_name):
        """New player appeared - defer initialization."""
        if self._destroyed:
            return
        GLib.idle_add(self._init_player, player_name)

    def _on_player_vanished(self, manager, player):
        """Player vanished - find by object identity, don't query the player."""
        if self._destroyed:
            return

        vanished_name = None
        for name, p in list(self._players.items()):
            if p is player:
                vanished_name = name
                break

        if vanished_name:
            del self._players[vanished_name]

            if self._current_player_name == vanished_name:
                self._current_player_name = None
                self._player_valid = False
                self._cached_metadata = {}

                # Switch to another player if available
                if self._players:
                    self._current_player_name = next(iter(self._players.keys()))
                    self._player_valid = True
                    GLib.idle_add(self._fetch_metadata)
                else:
                    self.emit("metadata-changed")

                self.emit("player-changed")

    def _on_metadata_signal(self, player, metadata):
        """Metadata signal - defer actual property access."""
        if self._destroyed:
            return

        # Check if this is our current player by object identity
        current_player = self._players.get(self._current_player_name)
        if player is not current_player:
            return

        # Defer the actual metadata fetch to avoid issues in signal context
        GLib.idle_add(self._fetch_metadata)

    def _on_status_signal(self, player, status):
        """Playback status signal - status is passed directly, safe to use."""
        if self._destroyed:
            return

        current_player = self._players.get(self._current_player_name)
        if player is not current_player:
            return

        self._cached_metadata["status"] = status
        self.emit("status-changed", status)

    def _fetch_metadata(self):
        """Fetch metadata from current player - called via idle_add."""
        if self._destroyed or not self._player_valid:
            return False

        player = self._players.get(self._current_player_name)
        if not player:
            self._player_valid = False
            return False

        try:
            metadata = player.props.metadata
            if metadata:
                md = dict(metadata.unpack())
                self._cached_metadata = {
                    "title": md.get("xesam:title", ""),
                    "artist": (md.get("xesam:artist") or [""])[0],
                    "length": md.get("mpris:length", 0),
                    "status": player.props.playback_status,
                    "position": 0,
                }
                # Try to get position
                try:
                    self._cached_metadata["position"] = player.get_position() or 0
                except Exception:
                    pass

                self.emit("metadata-changed")
            else:
                self._cached_metadata = {}
                self.emit("metadata-changed")

        except Exception as e:
            print(f"Error fetching metadata: {e}")
            # Player might be dead
            self._handle_player_dead()

        return False

    def _handle_player_dead(self):
        """Handle when we detect the player is dead."""
        if self._current_player_name and self._current_player_name in self._players:
            del self._players[self._current_player_name]

        self._current_player_name = None
        self._player_valid = False
        self._cached_metadata = {}

        if self._players:
            self._current_player_name = next(iter(self._players.keys()))
            self._player_valid = True
            GLib.idle_add(self._fetch_metadata)
        else:
            self.emit("metadata-changed")

        self.emit("player-changed")

    def update_position(self):
        """Update cached position - called by popup for slider updates."""
        if self._destroyed or not self._player_valid:
            return

        player = self._players.get(self._current_player_name)
        if not player:
            return

        try:
            self._cached_metadata["position"] = player.get_position() or 0
        except Exception:
            # Don't crash, just keep old position
            pass

    def get_cached_metadata(self):
        """Get cached metadata."""
        if not self._player_valid:
            return {}
        return self._cached_metadata.copy()

    def player_action(self, action, value=None):
        """Perform a player action safely."""
        if self._destroyed or not self._player_valid:
            return

        player = self._players.get(self._current_player_name)
        if not player:
            return

        try:
            if action == "play_pause":
                status = self._cached_metadata.get("status")
                if status == Playerctl.PlaybackStatus.PLAYING:
                    player.pause()
                else:
                    player.play()
            elif action == "next":
                player.next()
            elif action == "previous":
                player.previous()
            elif action == "seek" and value is not None:
                player.set_position(value)
                player.play()
        except Exception as e:
            print(f"Error performing action {action}: {e}")
            self._handle_player_dead()

    def check_players(self):
        """Check if we have players and select one if needed."""
        if self._destroyed:
            return

        # If no current player but we have players, pick one
        if not self._current_player_name and self._players:
            self._current_player_name = next(iter(self._players.keys()))
            self._player_valid = True
            self._fetch_metadata()
            self.emit("player-changed")

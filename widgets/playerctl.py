import re
from gi.repository import GObject, GLib, Playerctl, Gtk
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from shared.widget_container import EventBoxWidget
from shared import Popover
from utils.icons import icons
from utils import BarConfig
from widgets.common.resolver import create_slide_revealer, set_expanded, on_leave


class PlayerctlMenu(Popover):
    """Popover menu showing track info, slider for position, and current/total time."""

    POLL_INTERVAL_MS = 1000

    def __init__(self, point_to_widget, player):
        self.player = player

        # Main vertical box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_name("playerctl-menu")

        # Track frame
        self.track_frame = Gtk.Frame()
        self.track_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.track_frame.set_name("playerctl-track-frame")
        self.track_frame.set_margin_top(6)
        self.track_frame.set_margin_bottom(6)
        self.track_frame.set_margin_start(6)
        self.track_frame.set_margin_end(6)

        # Track info vertical box
        track_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # Title label
        self.title_label = Label(label="", style_classes="panel-text-title")
        self.title_label.set_halign(Gtk.Align.START)

        # Artist label
        self.artist_label = Label(label="", style_classes="panel-text-artist")
        self.artist_label.set_halign(Gtk.Align.START)

        # === FIXED: Explicit valid adjustment for slider ===
        adjustment = Gtk.Adjustment(
            value=0, lower=0, upper=1, step_increment=1, page_increment=5, page_size=0
        )
        self.slider = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment
        )
        self.slider.set_draw_value(False)
        self.slider.set_hexpand(True)
        self.slider.set_sensitive(False)

        # Time label
        self.time_label = Label(label="0:00 / 0:00", style_classes="panel-text-time")
        self.time_label.set_halign(Gtk.Align.END)

        # Slider + time container
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        time_box.set_hexpand(True)
        time_box.set_size_request(1, -1)  # ensure non-zero width
        time_box.pack_start(self.slider, True, True, 0)
        time_box.pack_end(self.time_label, False, False, 0)

        # Pack widgets into track box
        track_box.pack_start(self.title_label, False, False, 0)
        track_box.pack_start(self.artist_label, False, False, 0)
        track_box.pack_start(time_box, False, False, 0)

        self.track_frame.add(track_box)
        content_box.add(self.track_frame)
        content_box.show_all()

        super().__init__(content=content_box, point_to=point_to_widget)

        # Initial update
        self.update_track_info()
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._update_slider)

    def update_track_info(self):
        """Update title, artist, and slider/time values."""
        if (
            not self.player
            or not getattr(self.player, "props", None)
            or not self.player.props.metadata
        ):
            self.title_label.set_text("")
            self.artist_label.set_text("")
            self.time_label.set_text("0:00 / 0:00")
            if self.slider:
                adj = self.slider.get_adjustment()
                if adj:
                    adj.set_value(0)
            return

        metadata_variant = self.player.props.metadata
        metadata = dict(metadata_variant.unpack()) if metadata_variant else {}

        title = metadata.get("xesam:title", "")
        artists = metadata.get("xesam:artist", [])
        artist = artists[0] if artists else ""

        self.title_label.set_text(re.sub(r"\r?\n", " ", title))
        self.artist_label.set_text(re.sub(r"\r?\n", " ", artist))

        pos_us = (
            self.player.get_position() if hasattr(self.player, "get_position") else 0
        )
        length_us = metadata.get("mpris:length", 0)

        pos_sec_total = int(pos_us / 1_000_000)
        total_sec_total = int(length_us / 1_000_000)

        pos_min, pos_sec = divmod(pos_sec_total, 60)
        total_min, total_sec = divmod(total_sec_total, 60)

        # Update time text
        self.time_label.set_text(f"{pos_min}:{pos_sec:02} / {total_min}:{total_sec:02}")

        # Update slider adjustment safely
        adj = self.slider.get_adjustment()
        if adj:
            adj.set_upper(total_sec_total if total_sec_total > 0 else 1)
            adj.set_value(pos_sec_total)

    def _update_slider(self):
        """Update position/length every poll tick."""
        if (
            not self.player
            or not getattr(self.player, "props", None)
            or not self.player.props.metadata
        ):
            if self.slider:
                adj = self.slider.get_adjustment()
                if adj:
                    adj.set_value(0)
            self.time_label.set_text("0:00 / 0:00")
            return True

        pos_us = (
            self.player.get_position() if hasattr(self.player, "get_position") else 0
        )
        pos_sec_total = int(pos_us / 1_000_000)

        metadata_variant = self.player.props.metadata
        metadata = dict(metadata_variant.unpack()) if metadata_variant else {}
        length_us = metadata.get("mpris:length", 0)
        total_sec_total = int(length_us / 1_000_000)

        pos_min, pos_sec = divmod(pos_sec_total, 60)
        total_min, total_sec = divmod(total_sec_total, 60)

        # Update time display
        self.time_label.set_text(f"{pos_min}:{pos_sec:02} / {total_min}:{total_sec:02}")

        # === FIX: Update through adjustment, not raw slider calls ===
        adj = self.slider.get_adjustment()
        if adj:
            adj.set_upper(total_sec_total if total_sec_total > 0 else 1)
            adj.set_value(pos_sec_total)

        return True


class PlayerctlWidget(EventBoxWidget):
    """Playerctl widget with icon, slide reveal, and popover menu."""

    POLL_INTERVAL_MS = 2000

    def __init__(self, widget_config=None, **kwargs):
        if widget_config is None:
            widget_config = BarConfig()
        config = widget_config.get("playerctl", widget_config)
        super().__init__(**kwargs)

        self.config = config
        self.player = None
        self.player_manager = Playerctl.PlayerManager.new()
        self.popup = None

        # Configuration
        self.icon_size = self.config.get("icon_size", 16)
        self.slide_direction = self.config.get("slide_direction", "left")
        self.transition_duration = self.config.get("transition_duration", 250)
        self.tooltip_enabled = self.config.get("tooltip", True)

        # Icon
        self.icon_widget = Image(
            icon_name=icons["playerctl"]["music"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )

        # Track label
        self.label = Label(label="", style_classes="panel-text")
        self.revealer = create_slide_revealer(
            child=self.label,
            slide_direction=self.slide_direction,
            transition_duration=self.transition_duration,
            initially_revealed=False,
        )

        # Layout order
        if self.slide_direction == "right":
            self.box.add(self.icon_widget)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(self.icon_widget)

        self.box.set_hexpand(True)
        self.box.set_size_request(1, -1)
        self.box.show_all()

        # Connect player manager signals
        self.player_manager.connect("player-vanished", self._on_player_vanished)
        self.player_manager.connect("name-appeared", self._on_player_appeared)
        self._setup_initial_player()
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_players)

        # Hover expand/collapse (toggle_icon=None prevents crash)
        self.connect(
            "enter-notify-event",
            lambda *a: set_expanded(
                revealer=self.revealer,
                toggle_icon=None,
                slide_direction=self.slide_direction,
                icon_size=self.icon_size,
                expanded=True,
            ),
        )
        self.connect(
            "leave-notify-event",
            lambda w, e: on_leave(
                widget=w,
                event=e,
                revealer=self.revealer,
                slide_direction=self.slide_direction,
                toggle_icon=None,
                icon_size=self.icon_size,
            ),
        )

        # Click to open menu
        self.connect("button-press-event", self.on_click)

    def on_click(self, *_):
        if self.popup:
            self.popup.destroy()
            self.popup = None

        if not self.player:
            return

        self.popup = PlayerctlMenu(self, self.player)
        self.popup.update_track_info()
        self.popup.open()

    def _setup_initial_player(self):
        player_names = self.player_manager.props.player_names
        if player_names and isinstance(player_names[0], Playerctl.PlayerName):
            player_name_obj = player_names[0]
            player = Playerctl.Player.new_from_name(player_name_obj)
            self._set_player(player)

    def _poll_players(self):
        player_names = self.player_manager.props.player_names
        if not player_names and self.player:
            self._clear_player()
        elif player_names:
            current = (
                getattr(self.player.props, "player_name", None) if self.player else None
            )
            available = [p for p in player_names]

            if current not in available:
                player = Playerctl.Player.new_from_name(available[0])
                self._set_player(player)

        return True

    def _on_player_vanished(self, _, player):
        if self.player and getattr(player, "props", None):
            if player.props.player_name == self.player.props.player_name:
                self._clear_player()

    def _on_player_appeared(self, _, player_name_obj):
        if not self.player and isinstance(player_name_obj, Playerctl.PlayerName):
            player = Playerctl.Player.new_from_name(player_name_obj)
            self._set_player(player)

    def _set_player(self, player):
        if self.player:
            try:
                self.player.disconnect_by_func(self._on_metadata_changed)
            except TypeError:
                pass

        self.player = player
        if player:
            player.connect("metadata", self._on_metadata_changed)
            self._on_metadata_changed(player)

    def _on_metadata_changed(self, player, metadata=None):
        if not self.player or not getattr(player, "props", None):
            return

        metadata_variant = player.props.metadata
        md = dict(metadata_variant.unpack()) if metadata_variant else {}
        title = md.get("xesam:title", "")
        artists = md.get("xesam:artist", [])
        artist = artists[0] if artists else ""

        display_text = f"{title} – {artist}" if artist else title
        self.label.set_text(display_text)

        if self.tooltip_enabled:
            self.set_tooltip_text(display_text)

        if self.popup:
            self.popup.update_track_info()

    def _clear_player(self):
        self.player = None
        self.label.set_text("")
        if self.tooltip_enabled:
            self.set_tooltip_text("")
        if self.popup:
            self.popup.destroy()
            self.popup = None

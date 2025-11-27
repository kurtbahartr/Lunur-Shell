import re
from gi.repository import GObject, GLib, Playerctl, Gtk
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from shared.widget_container import EventBoxWidget
from shared import Popover
from utils.icons import icons
from utils import BarConfig, run_in_thread
from widgets.common.resolver import create_slide_revealer, set_expanded, on_leave


class PlayerctlMenu(Popover):
    POLL_INTERVAL_MS = 1000

    def __init__(self, point_to_widget, player):
        self.player = player
        self.icon_size = 16

        # Main container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_name("playerctl-menu")

        # Track frame
        self.track_frame = Gtk.Frame()
        self.track_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.track_frame.set_name("playerctl-track-frame")
        for side in ("top", "bottom", "start", "end"):
            getattr(self.track_frame, f"set_margin_{side}")(6)

        # Labels
        self.title_label = Label(label="", style_classes="panel-text-title")
        self.artist_label = Label(label="", style_classes="panel-text-artist")
        self.time_label = Label(label="0:00 / 0:00", style_classes="panel-text-time")
        self.title_label.set_halign(Gtk.Align.START)
        self.artist_label.set_halign(Gtk.Align.START)
        self.time_label.set_halign(Gtk.Align.END)

        # Slider
        adj = Gtk.Adjustment(
            value=0, lower=0, upper=1, step_increment=1, page_increment=5, page_size=0
        )
        self.slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self.slider.set_draw_value(False)
        self.slider.set_hexpand(True)
        self.slider.set_sensitive(True)
        self.slider.connect("button-press-event", self._on_slider_click)

        # Play/Pause Button
        self.play_pause_button = Gtk.Button()
        self.play_pause_button.set_name("playerctl-play-pause")
        self.play_pause_button.connect("clicked", self._on_play_pause_clicked)

        # Play/Pause Icon
        self.play_pause_icon = Image(
            icon_name=icons["playerctl"]["paused"],  # Default to paused icon
            icon_size=16,
            style_classes=["panel-icon"],
        )
        self.play_pause_button.add(self.play_pause_icon)

        # Layout
        track_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        time_box.set_hexpand(True)
        time_box.pack_start(self.slider, True, True, 0)
        time_box.pack_end(self.time_label, False, False, 0)

        track_box.pack_start(self.title_label, False, False, 0)
        track_box.pack_start(self.artist_label, False, False, 0)
        track_box.pack_start(time_box, False, False, 0)
        track_box.pack_start(self.play_pause_button, False, False, 6)

        self.track_frame.add(track_box)

        content_box.add(self.track_frame)
        content_box.show_all()
        super().__init__(content=content_box, point_to=point_to_widget)

        # Add method to match the previous implementation
        self._update_track_info_async()
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_tick)

        # Initial icon state
        self._update_play_pause_icon()

    def _on_play_pause_clicked(self, *args):
        if not self.player:
            return
        try:
            if self.player.props.playback_status == Playerctl.PlaybackStatus.PLAYING:
                self.player.pause()
            else:
                self.player.play()
        except Exception as e:
            print(f"Error toggling play/pause: {e}")

    def _update_play_pause_icon(self):
        if not self.player:
            return

        try:
            status = self.player.props.playback_status
            if status == Playerctl.PlaybackStatus.PLAYING:
                icon_name = icons["playerctl"]["playing"]
            else:
                icon_name = icons["playerctl"]["paused"]

            # Update icon on the main thread
            GLib.idle_add(self._set_play_pause_icon, icon_name)
        except Exception as e:
            print(f"Error updating play/pause icon: {e}")

    def _set_play_pause_icon(self, icon_name):
        try:
            self.play_pause_icon.set_from_icon_name(icon_name)
        except Exception as e:
            print(f"Error setting play/pause icon: {e}")

    @run_in_thread
    def _update_track_info_async(self):
        if (
            not self.player
            or not getattr(self.player, "props", None)
            or not self.player.props.metadata
        ):
            GLib.idle_add(self._reset_display)
            return

        try:
            md = dict(self.player.props.metadata.unpack())
            title = md.get("xesam:title", "")
            artist = md.get("xesam:artist", [None])[0] or ""
            length_us = md.get("mpris:length", 0)
            pos_us = (
                self.player.get_position()
                if hasattr(self.player, "get_position")
                else 0
            )

            cur_sec, total_sec = int(pos_us / 1e6), int(length_us / 1e6)
            cur_min, cur_s = divmod(cur_sec, 60)
            tot_min, tot_s = divmod(total_sec, 60)
            time_text = f"{cur_min}:{cur_s:02} / {tot_min}:{tot_s:02}"

            GLib.idle_add(
                self._update_labels_and_slider,
                title,
                artist,
                time_text,
                cur_sec,
                total_sec,
            )

            # Also update play/pause icon
            self._update_play_pause_icon()
        except Exception as e:
            print(f"Error in track info update: {e}")

    def _update_labels_and_slider(self, title, artist, time_text, cur_sec, total_sec):
        # Update labels
        self.title_label.set_text(re.sub(r"\r?\n", " ", title))
        self.artist_label.set_text(re.sub(r"\r?\n", " ", artist))
        self.time_label.set_text(time_text)

        # Update slider
        adj = self.slider.get_adjustment()
        if adj:
            adj.set_upper(max(total_sec, 1))
            adj.set_value(cur_sec)

    def _poll_tick(self):
        if self.player:
            self._update_track_info_async()
        return True

    def _on_slider_click(self, widget, event):
        if not self.player:
            return False

        alloc = widget.get_allocation()
        if alloc.width <= 0:
            return False

        fraction = max(0, min(event.x / alloc.width, 1))
        total_sec = widget.get_adjustment().get_upper()
        seek_sec = int(total_sec * fraction)

        try:
            if hasattr(self.player, "set_position"):
                self.player.set_position(seek_sec * 1_000_000)
            if hasattr(self.player, "play"):
                self.player.play()
        except Exception as e:
            print(f"Error seeking in track: {e}")
        return False

    def _reset_display(self):
        """Reset all display elements when no player is active."""
        # Reset labels
        self.title_label.set_text("")
        self.artist_label.set_text("")
        self.time_label.set_text("0:00 / 0:00")

        # Reset slider
        adj = self.slider.get_adjustment()
        if adj:
            adj.set_value(0)
            adj.set_upper(1)

        # Reset play/pause icon
        GLib.idle_add(self._set_play_pause_icon, icons["playerctl"]["paused"])


class PlayerctlWidget(EventBoxWidget):
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

        self.icon_size = self.config.get("icon_size", 16)
        self.slide_direction = self.config.get("slide_direction", "left")
        self.transition_duration = self.config.get("transition_duration", 250)
        self.tooltip_enabled = self.config.get("tooltip", True)

        self.icon_widget = Image(
            icon_name=icons["playerctl"]["music"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )
        self.label = Label(label="", style_classes="panel-text")

        label_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label_container.pack_start(self.label, True, True, 6)

        self.revealer = create_slide_revealer(
            child=label_container,
            slide_direction=self.slide_direction,
            transition_duration=self.transition_duration,
            initially_revealed=False,
        )

        if self.slide_direction == "right":
            self.box.add(self.icon_widget)
            self.box.add(self.revealer)
        else:
            self.box.add(self.revealer)
            self.box.add(self.icon_widget)

        self.box.set_hexpand(True)
        self.box.set_size_request(1, -1)
        self.box.show_all()

        # Connect signals
        self.player_manager.connect("player-vanished", self._on_player_vanished)
        self.player_manager.connect("name-appeared", self._on_player_appeared)
        self._setup_initial_player()
        GLib.timeout_add(self.POLL_INTERVAL_MS, self._poll_players)

        # Hover reveal
        self.connect(
            "enter-notify-event",
            lambda *a: set_expanded(
                self.revealer, None, self.slide_direction, self.icon_size, expanded=True
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
        # Click menu
        self.connect("button-press-event", self.on_click)

    def on_click(self, *_):
        if self.popup:
            self.popup.destroy()
            self.popup = None
        if not self.player:
            return
        self.popup = PlayerctlMenu(self, self.player)
        self.popup.open()

    @run_in_thread
    def _on_metadata_changed(self, player, metadata=None):
        if not self.player or not getattr(player, "props", None):
            return
        md = dict(player.props.metadata.unpack()) if player.props.metadata else {}
        title = md.get("xesam:title", "")
        artist = md.get("xesam:artist", [])
        artist = artist[0] if artist else ""
        display_text = f"{title} – {artist}" if artist else title
        GLib.idle_add(self._update_label_text, display_text)

    def _update_label_text(self, text):
        self.label.set_text(text)
        if self.tooltip_enabled:
            self.set_tooltip_text(text)
        if self.popup:
            self.popup._update_track_info_async()

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

    def _clear_player(self):
        self.player = None
        self.label.set_text("")
        if self.tooltip_enabled:
            self.set_tooltip_text("")
        if self.popup:
            self.popup.destroy()
            self.popup = None

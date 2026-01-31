# widgets/playerctl.py

import re
from gi.repository import GLib, Playerctl, Gtk
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from shared.pop_over import Popover
from shared.reveal import HoverRevealer
from utils.icons import icons
from utils.widget_settings import BarConfig


class PlayerctlMenu(Popover):
    """
    The popup menu containing playback controls, seek bar, and track info.
    """

    __slots__ = (
        "service",
        "config",
        "icon_size",
        "poll_interval",
        "_poll_source_id",
        "_destroyed",
        "track_frame",
        "title_label",
        "artist_label",
        "time_label",
        "slider",
        "skip_back_button",
        "skip_back_icon",
        "play_pause_button",
        "play_pause_icon",
        "skip_forward_button",
        "skip_forward_icon",
    )

    def __init__(self, point_to_widget, service, config=None):
        self.service = service
        self.config = config or {}
        self.icon_size = self.config.get("icon_size", 16)
        self.poll_interval = self.config.get("menu_poll_interval", 1000)
        self._poll_source_id = None
        self._destroyed = False

        # Build UI
        content_box = self._build_ui()

        super().__init__(content=content_box, point_to=point_to_widget)

        self.connect("destroy", self._on_destroy)

        # Update display with cached data only (no blocking calls)
        self._update_track_info()

        # Defer poll start to idle to avoid blocking popup open
        GLib.idle_add(self._start_poll)

    def _build_ui(self):
        """Build the menu UI structure."""
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content_box.set_name("playerctl-menu")
        content_box.set_halign(Gtk.Align.FILL)
        content_box.set_hexpand(True)

        # Track frame
        self.track_frame = Gtk.Frame()
        self.track_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.track_frame.set_name("playerctl-track-frame")
        for side in ("top", "bottom", "start", "end"):
            getattr(self.track_frame, f"set_margin_{side}")(2)

        # Labels
        self.title_label = Label(label="", style_classes="panel-text-title")
        self.artist_label = Label(label="", style_classes="panel-text-artist")
        self.time_label = Label(label="0:00 / 0:00", style_classes="panel-text-time")
        self.title_label.set_halign(Gtk.Align.FILL)
        self.artist_label.set_halign(Gtk.Align.FILL)
        self.time_label.set_halign(Gtk.Align.END)

        # Slider
        adj = Gtk.Adjustment(
            value=0, lower=0, upper=1, step_increment=1, page_increment=5
        )
        self.slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self.slider.set_draw_value(False)
        self.slider.set_hexpand(True)
        self.slider.set_halign(Gtk.Align.FILL)
        self.slider.connect("button-press-event", self._on_slider_click)

        # Control buttons
        self.skip_back_button = Gtk.Button()
        self.skip_back_button.connect(
            "clicked", lambda *_: self._player_action("previous")
        )
        self.skip_back_icon = Image(
            icon_name=icons["playerctl"]["prev"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )
        self.skip_back_button.add(self.skip_back_icon)

        self.play_pause_button = Gtk.Button()
        self.play_pause_button.connect(
            "clicked", lambda *_: self._player_action("play_pause")
        )
        self.play_pause_icon = Image(
            icon_name=icons["playerctl"]["paused"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )
        self.play_pause_button.add(self.play_pause_icon)

        self.skip_forward_button = Gtk.Button()
        self.skip_forward_button.connect(
            "clicked", lambda *_: self._player_action("next")
        )
        self.skip_forward_icon = Image(
            icon_name=icons["playerctl"]["next"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )
        self.skip_forward_button.add(self.skip_forward_icon)

        # Layout
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls_box.set_halign(Gtk.Align.CENTER)
        controls_box.pack_start(self.skip_back_button, False, False, 0)
        controls_box.pack_start(self.play_pause_button, False, False, 0)
        controls_box.pack_start(self.skip_forward_button, False, False, 0)

        track_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        track_box.pack_start(self.title_label, False, False, 0)
        track_box.pack_start(self.artist_label, False, False, 0)

        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        time_box.pack_start(self.slider, True, True, 0)
        time_box.pack_end(self.time_label, False, False, 0)
        track_box.pack_start(time_box, False, False, 0)
        track_box.pack_start(controls_box, False, False, 2)

        self.track_frame.add(track_box)
        content_box.add(self.track_frame)
        content_box.show_all()

        return content_box

    def _start_poll(self):
        """Start the polling timer (called from idle)."""
        if not self._destroyed and self._poll_source_id is None:
            self._poll_source_id = GLib.timeout_add(self.poll_interval, self._poll_tick)
        return False

    def _on_destroy(self, *args):
        """Clean up resources."""
        self._destroyed = True
        if self._poll_source_id is not None:
            GLib.source_remove(self._poll_source_id)
            self._poll_source_id = None

    def _player_action(self, action, *args):
        """Execute player action if not destroyed."""
        if not self._destroyed:
            self.service.player_action(action, *args)

    def _update_play_pause_icon(self, status):
        """Update play/pause button icon based on playback status."""
        if self._destroyed:
            return

        icon_name = (
            icons["playerctl"]["playing"]
            if status == Playerctl.PlaybackStatus.PLAYING
            else icons["playerctl"]["paused"]
        )
        self.play_pause_icon.set_from_icon_name(icon_name)

    def _update_track_info(self):
        """Update display with cached metadata (non-blocking)."""
        if self._destroyed:
            return

        metadata = self.service.get_cached_metadata()
        if not metadata:
            self._reset_display()
            return

        title = metadata.get("title", "")
        artist = metadata.get("artist", "")
        length_us = metadata.get("length", 0)
        status = metadata.get("status", Playerctl.PlaybackStatus.STOPPED)
        pos_us = metadata.get("position", 0)

        # Format time
        cur_sec = int(pos_us / 1_000_000)
        total_sec = int(length_us / 1_000_000)
        cur_min, cur_s = divmod(cur_sec, 60)
        tot_min, tot_s = divmod(total_sec, 60)
        time_text = f"{cur_min}:{cur_s:02} / {tot_min}:{tot_s:02}"

        # Update UI
        self.title_label.set_text(self._sanitize_text(title, 30))
        self.artist_label.set_text(self._sanitize_text(artist, 30))
        self.time_label.set_text(time_text)

        # Update slider
        adj = self.slider.get_adjustment()
        adj.set_upper(max(total_sec, 1))
        adj.set_value(cur_sec)

        self._update_play_pause_icon(status)

    def _sanitize_text(self, text, max_len):
        """Remove newlines and truncate text."""
        import utils.functions as helpers

        return helpers.truncate(re.sub(r"\r?\n", " ", text), max_len)

    def _poll_tick(self):
        """Periodic update callback."""
        if self._destroyed:
            self._poll_source_id = None
            return False

        self.service.update_position()
        self._update_track_info()
        return True

    def _on_slider_click(self, widget, event):
        """Handle slider click to seek."""
        if self._destroyed:
            return False

        alloc = widget.get_allocation()
        if alloc.width <= 0:
            return False

        fraction = max(0.0, min(event.x / alloc.width, 1.0))
        total_sec = widget.get_adjustment().get_upper()
        seek_us = int(total_sec * fraction * 1_000_000)

        self.service.player_action("seek", seek_us)
        return False

    def _reset_display(self):
        """Reset display to empty state."""
        if self._destroyed:
            return

        self.title_label.set_text("")
        self.artist_label.set_text("")
        self.time_label.set_text("0:00 / 0:00")

        adj = self.slider.get_adjustment()
        adj.set_value(0)
        adj.set_upper(1)

        self.play_pause_icon.set_from_icon_name(icons["playerctl"]["paused"])


class PlayerctlWidget(HoverRevealer):
    """
    Main playerctl widget for the bar.
    Defers service initialization until widget is realized.
    """

    __slots__ = (
        "config",
        "icon_size",
        "tooltip_enabled",
        "poll_interval",
        "popup",
        "service",
        "_poll_source_id",
        "_destroyed",
        "_service_initialized",
        "icon_widget",
        "label",
    )

    def __init__(self, widget_config: BarConfig | None = None, **kwargs):
        safe_config = widget_config if widget_config is not None else {}
        config = safe_config.get("playerctl", safe_config)

        self.config = config
        self.icon_size = config.get("icon_size", 16)
        self.tooltip_enabled = config.get("tooltip", True)
        self.poll_interval = config.get("poll_interval", 2000)

        self.popup = None
        self.service = None
        self._poll_source_id = None
        self._destroyed = False
        self._service_initialized = False

        # Build UI
        self.icon_widget = Image(
            icon_name=icons["playerctl"]["music"],
            icon_size=self.icon_size,
            style_classes=["panel-icon"],
        )

        self.label = Label(label="", style_classes="panel-text")
        label_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label_container.pack_start(self.label, True, True, 4)
        label_container.set_hexpand(True)

        slide_direction = config.get("slide_direction", "left")
        transition_duration = config.get("transition_duration", 250)

        super().__init__(
            visible_child=self.icon_widget,
            hidden_child=label_container,
            slide_direction=slide_direction,
            transition_duration=transition_duration,
            expanded_margin=self.icon_size,
            **kwargs,
        )

        # Defer service initialization until widget is realized
        self.connect("realize", self._on_realize)
        self.connect("destroy", self._on_destroy)

    def _on_realize(self, *args):
        """Initialize service when widget becomes visible."""
        if not self._service_initialized and not self._destroyed:
            GLib.idle_add(self._init_service)

    def _init_service(self):
        """Lazy initialize the playerctl service."""
        if self._service_initialized or self._destroyed:
            return False

        try:
            from services.playerctl import PlayerctlService

            self.service = PlayerctlService()
            self.service.connect("metadata-changed", self._on_metadata_changed)
            self.service.connect("player-changed", self._on_player_changed)

            self._service_initialized = True

            # Start polling
            self._poll_source_id = GLib.timeout_add(self.poll_interval, self._poll_tick)

        except ImportError:
            # Gracefully disable widget
            self.icon_widget.set_opacity(0.3)
            if self.tooltip_enabled:
                self.set_tooltip_text("Playerctl not available")

        return False

    def _on_destroy(self, *args):
        """Clean up resources."""
        self._destroyed = True

        if self._poll_source_id is not None:
            GLib.source_remove(self._poll_source_id)
            self._poll_source_id = None

        if self.service:
            self.service.destroy()
            self.service = None

        if self.popup:
            self.popup.destroy()
            self.popup = None

    def _on_metadata_changed(self, service):
        """Handle metadata changed signal from service."""
        if not self._destroyed:
            self._update_display()

    def _on_player_changed(self, service):
        """Handle player changed signal from service."""
        if self._destroyed:
            return

        if not self.service or not self.service.is_valid:
            self._clear_display()

    def _update_display(self):
        """Update the label with cached metadata."""
        if self._destroyed:
            return

        if not self.service:
            return

        metadata = self.service.get_cached_metadata()
        if not metadata:
            self._clear_display()
            return

        title = metadata.get("title", "")
        artist = metadata.get("artist", "")

        # Format display text
        if artist:
            display_text = f"{title} – {artist}"
        else:
            display_text = title

        import utils.functions as helpers

        display_text = helpers.truncate(display_text, 20)

        self.label.set_text(display_text)

        if self.tooltip_enabled:
            self.set_tooltip_text(display_text)

    def _clear_display(self):
        """Clear the display."""
        if self._destroyed:
            return

        self.label.set_text("")

        if self.tooltip_enabled:
            self.set_tooltip_text("")

        if self.popup:
            self.popup.destroy()
            self.popup = None

    def on_click(self, widget, event):
        """
        Override HoverRevealer.on_click to open the popup.
        Ensure service is initialized before opening menu.
        """
        if self.popup:
            self.popup.destroy()
            self.popup = None
            return

        # Ensure service is ready
        if not self._service_initialized:
            GLib.idle_add(self._init_service)
            return

        if not self.service or not self.service.is_valid:
            return

        self.popup = PlayerctlMenu(self, self.service, config=self.config)
        self.popup.open()

    def _poll_tick(self):
        """Periodic poll to check state."""
        if self._destroyed:
            self._poll_source_id = None
            return False

        if self.service:
            self.service.check_players()

        return True

# widgets/quick_settings/submenu/hyprsunset.py

import json
import os
from fabric.hyprland.widgets import get_hyprland_connection
from fabric.utils import cooldown, exec_shell_command_async, invoke_repeater
from fabric.widgets.scale import Scale
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from gi.repository import Gtk, GLib

from shared.buttons import QSChevronButton
from shared.submenu import QuickSubMenu
from shared.separator import Separator
from utils.functions import is_app_running, toggle_command
from utils.icons import text_icons

CACHE_DIR = os.path.expanduser("~/.cache/fabric")
STATE_FILE = os.path.join(CACHE_DIR, "hyprsunset.json")


class HyprSunsetSubMenu(QuickSubMenu):
    def __init__(self, **kwargs):
        self.scan_button = None
        self._hyprland_connection = None
        self._repeater_id = None

        self.cached_temp = self.load_state()

        self.scale_icon = Label(
            label=text_icons["nightlight"]["enabled"],
            style_classes=["slider-icon"],
        )

        self.scale = Scale(
            name="hyprsunset-scale",
            draw_value=False,
            digits=0,
            increments=(100, 100),
            max_value=10000,
            min_value=1000,
            value=self.cached_temp,
            style_classes=["qs-slider"],
            h_expand=True,
        )

        self.value_label = Label(
            label=f"{self.cached_temp}K",
            style_classes=["slider-percentage"],
        )

        scale_container = Box(
            children=[self.scale_icon, self.scale, self.value_label],
            h_expand=True,
            v_expand=False,
            spacing=10,
        )

        self.separator = Separator(
            orientation="horizontal",
            style_classes=["app-volume-separator"],
        )

        main_container = Box(
            children=[self.separator, scale_container],
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
        )

        super().__init__(
            title="HyprSunset",
            title_icon=text_icons["nightlight"]["enabled"],
            name="hyprsunset-sub-menu",
            scan_button=self.scan_button,
            child=main_container,
            **kwargs,
        )

        self.scale.connect("value-changed", self.on_scale_move)

        # Lazy initialize the repeater only when submenu is revealed
        self.connect("notify::child-revealed", self._on_reveal_changed)

    def _on_reveal_changed(self, revealer, *args):
        """Start/stop the repeater based on reveal state."""
        if self.get_child_revealed():
            if self._repeater_id is None:
                self._repeater_id = invoke_repeater(1000, self.update_scale)
        else:
            if self._repeater_id is not None:
                GLib.source_remove(self._repeater_id)
                self._repeater_id = None

    def _get_hyprland_connection(self):
        if self._hyprland_connection is None:
            self._hyprland_connection = get_hyprland_connection()
        return self._hyprland_connection

    def load_state(self):
        try:
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)

            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    return int(data.get("temperature", 2600))
        except Exception:
            pass
        return 2600

    def save_state(self, temp):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"temperature": temp}, f)
        except Exception:
            pass

    def update_value_label(self, value: int):
        self.value_label.set_label(f"{value}K")

    @cooldown(0.1)
    def on_scale_move(self, scale: Scale):
        val = int(scale.get_value())
        self.update_value_label(val)
        self.save_state(val)

        if is_app_running("hyprsunset"):
            exec_shell_command_async(
                f"hyprctl hyprsunset temperature {val}",
                lambda *_: None,
            )
        return True

    def update_scale(self, *_):
        if is_app_running("hyprsunset"):
            exec_shell_command_async(
                "hyprctl hyprsunset temperature",
                self._update_ui_from_system,
            )
        return True

    def _update_ui_from_system(self, output: str | int):
        try:
            val = int(
                output.strip("\n").strip("") if isinstance(output, str) else output
            )
        except ValueError:
            return

        if abs(val - self.scale.get_value()) > 100:
            self.scale.set_value(val)
            self.save_state(val)
            self.update_value_label(val)


class HyprSunsetToggle(QSChevronButton):
    def __init__(self, submenu: QuickSubMenu = None, popup=None, **kwargs):
        self.popup = popup
        self._repeater_id = None
        self._is_running = False

        super().__init__(
            style_classes=["quicksettings-toggler"],
            action_icon=text_icons["nightlight"]["disabled"],
            pixel_size=20,
            action_label="Disabled",
            submenu=submenu,
            **kwargs,
        )

        self.action_button.set_sensitive(True)
        self.action_button.connect("clicked", self.on_action)

        # Do initial check but don't start repeater yet
        GLib.idle_add(self._initial_update)

    def _initial_update(self):
        """Perform initial update after widget is shown."""
        self.update_action_button()
        # Start repeater only after initial update
        if self._repeater_id is None:
            self._repeater_id = invoke_repeater(1000, self.update_action_button)
        return False

    def on_action(self, *_):
        if self.submenu is None:
            return True

        current_temp = int(self.submenu.scale.get_value())
        is_now_running = toggle_command("hyprsunset", f"hyprsunset -t {current_temp}")
        self.update_visuals(is_now_running)
        return True

    def update_action_button(self, *_):
        self._is_running = is_app_running("hyprsunset")
        self.update_visuals(self._is_running)
        return True

    def update_visuals(self, is_running):
        if is_running:
            self.action_icon.set_label(text_icons["nightlight"]["enabled"])
            self.action_label.set_label("Enabled")
            self.add_style_class("active")
        else:
            self.action_icon.set_label(text_icons["nightlight"]["disabled"])
            self.action_label.set_label("Disabled")
            self.remove_style_class("active")

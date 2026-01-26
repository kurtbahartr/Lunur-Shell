# widgets/quick_settings/quick_settings_menu.py

from gi.repository import Gtk
from fabric.widgets.box import Box
from fabric.widgets.grid import Grid
from .sliders.brightness import BrightnessSlider
from .sliders.volume import VolumeSlider
from .sliders.microphone import MicrophoneSlider
from .togglers import NotificationQuickSetting
from .submenu.wifi import WifiQuickSetting
from .submenu.bluetooth import BluetoothToggle, BluetoothSubMenu
from .submenu.hyprsunset import HyprSunsetSubMenu, HyprSunsetToggle
from shared.pop_over import Popover


class SlidersContainer(Box):
    """Container for brightness, volume, and microphone sliders."""

    __slots__ = ("brightness_slider", "volume_slider", "mic_slider")

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            style_classes="sliders-container",
        )
        # Create and pack all sliders in one go
        sliders = [BrightnessSlider(), VolumeSlider(), MicrophoneSlider()]

        for slider in sliders:
            self.pack_start(slider, False, False, 0)

        # Store references
        self.brightness_slider, self.volume_slider, self.mic_slider = sliders


class QuickSettingsMenu(Popover):
    """Quick settings menu with toggles and submenus."""

    __slots__ = (
        "_active_submenu",
        "sliders",
        "grid",
        "bt_submenu",
        "hyprsunset_submenu",
        "wifi_btn",
        "bt_btn",
        "notification_btn",
        "hyprsunset_btn",
    )

    def __init__(self, point_to_widget, config):
        self._active_submenu = None

        # Create content container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.set_name("quick-settings-menu")

        # Add sliders
        self.sliders = SlidersContainer()
        content_box.pack_start(self.sliders, False, False, 0)

        # Create grid
        self.grid = Grid(
            row_spacing=10,
            column_spacing=10,
            column_homogeneous=True,
            row_homogeneous=True,
        )

        # Create submenus once
        self.bt_submenu = BluetoothSubMenu()
        self.hyprsunset_submenu = HyprSunsetSubMenu()

        # Create all toggle buttons
        toggles = [
            (WifiQuickSetting(), 0, 0),
            (BluetoothToggle(submenu=self.bt_submenu), 1, 0),
            (NotificationQuickSetting(), 0, 1),
            (HyprSunsetToggle(submenu=self.hyprsunset_submenu), 1, 1),
        ]

        # Attach all toggles to grid and store references
        self.wifi_btn, self.bt_btn, self.notification_btn, self.hyprsunset_btn = [
            toggle for toggle, *_ in toggles
        ]

        for toggle, col, row in toggles:
            self.grid.attach(toggle, col, row, 1, 1)

        content_box.pack_start(self.grid, True, True, 0)

        for submenu in (self.bt_submenu, self.hyprsunset_submenu):
            if submenu.get_parent() is None:
                content_box.pack_start(submenu, False, False, 0)

        # Connect submenu toggles with partial application
        self._connect_submenu_toggles()

        content_box.show_all()
        super().__init__(content=content_box, point_to=point_to_widget)

    def _connect_submenu_toggles(self):
        """Connect reveal-clicked signals for submenus."""
        submenu_map = (
            (self.bt_btn, self.bt_submenu),
            (self.hyprsunset_btn, self.hyprsunset_submenu),
        )

        for button, submenu in submenu_map:
            button.connect("reveal-clicked", self._on_reveal_clicked, submenu)

    def _on_reveal_clicked(self, _button, submenu):
        """Handle reveal-clicked signal with submenu parameter."""
        self.toggle_submenu(submenu)

    def toggle_submenu(self, submenu):
        if self._active_submenu == submenu:
            # Close the same submenu
            submenu.toggle_reveal()
            self._active_submenu = None
            return

        # Close currently active submenu if different
        if self._active_submenu is not None:
            self._active_submenu.toggle_reveal()

        # Open new submenu
        submenu.toggle_reveal()
        self._active_submenu = submenu

from typing import TypedDict
from .types import Anchor, Layer


class WithLabelTooltip(TypedDict):
    label: bool
    tooltip: bool


class WithIconSize(TypedDict):
    icon_size: int


class SlidingWidget(WithLabelTooltip, WithIconSize):
    transition_duration: int
    slide_direction: str


class DateTimeMenu(TypedDict):
    clock_format: str
    format: str


class ScreenCorners(TypedDict):
    enabled: bool
    size: int


class General(TypedDict):
    screen_corners: ScreenCorners
    location: str
    layer: Layer
    debug: bool


class AppLauncher(WithIconSize):
    app_icon_size: int
    show_descriptions: bool


class Workspaces(TypedDict):
    count: int
    hide_unoccupied: bool
    ignored: list[int]
    reverse_scroll: bool
    empty_scroll: bool
    default_label_format: str
    icon_map: dict[str, str]


class Notification(TypedDict):
    enabled: bool
    ignored: list[str]
    timeout: int
    anchor: Anchor
    auto_dismiss: bool
    play_sound: bool
    sound_file: str
    max_count: int
    dismiss_on_hover: bool
    max_actions: int
    per_app_limits: dict[str, int]


class BatteryNotifications(TypedDict):
    enabled: bool
    full_battery: bool
    charging: bool
    low_battery: bool
    low_threshold: int


class Battery(WithLabelTooltip, WithIconSize):
    orientation: str
    full_battery_level: int
    hide_label_when_full: bool
    notifications: BatteryNotifications


class SystemTray(SlidingWidget):
    pass


class QuickSettings(TypedDict):
    bar_icons: list[str]
    show_ssid: bool
    show_audio_percent: bool
    show_brightness_percent: bool


class Keybinds(TypedDict):
    enabled: bool
    path: str


class WindowTitle(TypedDict):
    icon: bool
    truncation: bool
    truncation_size: int
    hide_when_zero: bool
    title_map: list[dict[str, str]]


class PowerProfiles(WithIconSize):
    pass


class Hyprpicker(WithIconSize):
    tooltip: bool


class Cliphist(WithLabelTooltip):
    icon: str


class Playerctl(SlidingWidget):
    pass


class EmojiPicker(WithLabelTooltip):
    icon: str
    per_row: int
    per_column: int


class Theme(TypedDict):
    name: str


class CollapsibleGroup(TypedDict):
    widgets: list[str]
    spacing: int
    style_classes: list[str]
    collapsed_icon: str
    slide_direction: str
    transition_duration: int


class Recording(WithIconSize):
    path: str
    tooltip: bool
    audio: bool


class Screenshot(WithLabelTooltip):
    enabled: bool
    icon: str
    path: str
    annotation: bool


class OSD(WithIconSize):
    osds: list[str]
    enabled: bool
    anchor: str
    timeout: int
    transition_type: str
    transition_duration: int
    percentage: bool
    orientation: str


type Sleep = WithLabelTooltip
type Reboot = WithLabelTooltip
type Logout = WithLabelTooltip
type Shutdown = WithLabelTooltip


class BarConfig(TypedDict):
    date_time: DateTimeMenu
    workspaces: Workspaces
    notifications: Notification
    battery: Battery
    system_tray: SystemTray
    quick_settings: QuickSettings
    general: General
    app_launcher: AppLauncher
    keybinds: Keybinds
    theme: Theme
    window_title: WindowTitle
    hyprpicker: Hyprpicker
    power_profiles: PowerProfiles
    cliphist: Cliphist
    playerctl: Playerctl
    collapsible_groups: list[CollapsibleGroup]
    sleep: Sleep
    reboot: Reboot
    logout: Logout
    shutdown: Shutdown
    screenshot: Screenshot
    recorder: Recording
    osd: OSD

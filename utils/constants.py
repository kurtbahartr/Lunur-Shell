from fabric.utils import get_relative_path
from gi.repository import GLib
from typing import TypedDict, List, Dict

APPLICATION_NAME = "Lunur-Shell"
SYSTEM_CACHE_DIR = GLib.get_user_cache_dir()
APP_CACHE_DIRECTORY = f"{SYSTEM_CACHE_DIR}/{APPLICATION_NAME}"


NOTIFICATION_CACHE_FILE = f"{APP_CACHE_DIRECTORY}/notifications.json"

ASSETS_DIR = get_relative_path("../assets/")

DEFAULT_CONFIG = {
    "date_time": {
        "clock_format": "24h",
        "format": "%b %d", 
    },
    "screenshot": {
        "path": "Pictures/Screenshots",
        "icon": "󰕸",
        "icon_size": 16,
        "label": False,
        "tooltip": True,
        "annotation": True,
    },
    "osd": {
        "osds": ["volume", "brightness"],
        "enable": True,
        "anchor": "bottom-center",
        "icon_size": 28,
        # "opacity": 90,
        "timeout": 3000,
        "transition_type": "slide-up",
        "transition_duration": 500,
        "percentage": True,
        "orientation": "horizontal",  
    },
    "recorder": {
        "path": "Videos/Screencasting",
        "audio": True,
        "icon_size": 16,
        "tooltip": True,
    },
    "sleep": {
        "label": False,
        "tooltip": True
    },
    "reboot": {
        "label": False,
        "tooltip": True
    },
    "logout": {
        "label": False,
        "tooltip": True
    },
    "shutdown": {
        "label": False,
        "tooltip": True
    },
    "quick_settings": {
        "icon_size": "16",
        "ignored": [],
        "bar_icons": ["network", "audio", "bluetooth", "brightness"],
        "show_ssid": False,
        "show_audio_percent": False,
        "show_brightness_percent": False,
        "style_classes": [ "compact" ],
    },
    "keybinds": {
        "enabled": True,
        "path": "~/.config/hypr/hyprbinds.conf",  
    },
    "app_launcher": {
        "icon_size": 16,
        "app_icon_size": 48,
        "show_descriptions": False,
    },
    "cliphist": {
        "icon": "",
        "label": False,
        "tooltip": True,
    },
    "playerctl": {
        "icon_size": 16,
        "slide_direction": "right",
        "transition_duration": 300,
        "tooltip": True,
    },
    "emoji_picker": {
        "icon": "",
        "label": False,
        "tooltip": True,
        "per_row": 9,
        "per_column": 4,
    },
    "general": {
        "layer": "top",
        "location":"top",
    },
    "screen_corners": {
        "enabled": False,
        "size": 20,
    },
    "collapsible_groups": [
        {
            "widgets": ["hyprpicker", "emoji_picker", "cliphist"],
            "spacing": 4,
            "style_classes": ["compact"],
            "collapsed_icon": "",
            "slide_direction": "left",
            "transition_duration": 300,
        },
    ],
    "layout": {
        "left_section": ["app_launcher", "workspaces"],
        "middle_section": ["date_time", "power_profiles"],
        "right_section": ["@group:0", "system_tray", "sleep", "reboot", "logout", "shutdown"],
    },
    "window_title": {
        "icon": True,
        "truncation": True,
        "truncation_size": 30,
        "title_map": [],
    },
    "workspaces": {
        "count": 3,
        "hide_unoccupied": False,
        "ignored": [],
        "reverse_scroll": False,
        "empty_scroll": False,
        "default_label_format": "{id}",
        "icon_map": {},  # Example: {"1": "🌐", "2": "🎨"}
    },
    "notification": {
        "enabled": True,
        "anchor": "top-right",
        "auto_dismiss": True,
        "ignored": [],
        "timeout": 3000,
        "max_count": 200,
        "transition_type": "slide-left",
        "transition_duration": 350,
        "per_app_limits": {},
        "play_sound": False,
        "max_actions": 5,
        "dismiss_on_hover": False,
        "sound_file": "notification4",
    },
    "battery": {
        "full_battery_level": 100,
        "hide_label_when_full": True,
        "label": True,
        "tooltip": True,
        "orientation": "vertical",
        "icon_size": 16,
        "notifications": {
            "enabled": True,
            "full_battery": True,
            "charging": True,
            "low_battery": True,
            "low_threshold": 10,
        },
    },
    "system_tray": {
        "icon_size": 16,
        "slide_direction": "right",
        "transition_duration": 300,
        "tooltip": True,
    },
    "hyprpicker": {
        "icon_size": 16,
        "tooltip": True,
    },
    "power_profiles": {
        "icon_size": 16,
    }
}

WINDOW_TITLE_MAP = [
    # Original Entries
    ["discord", "", "Discord"],
    ["vesktop", "", "Vesktop"],
    ["org.kde.dolphin", "", "Dolphin"],
    ["plex", "󰚺", "Plex"],
    ["steam", "", "Steam"],
    ["spotify", "󰓇", "Spotify"],
    ["spotube", "󰓇", "Spotify"],
    ["ristretto", "󰋩", "Ristretto"],
    ["obsidian", "󱓧", "Obsidian"],
    # Browsers
    ["google-chrome", "", "Google Chrome"],
    ["brave-browser", "󰖟", "Brave Browser"],
    ["firefox", "󰈹", "Firefox"],
    ["microsoft-edge", "󰇩", "Edge"],
    ["chromium", "", "Chromium"],
    ["opera", "", "Opera"],
    ["vivaldi", "󰖟", "Vivaldi"],
    ["waterfox", "󰖟", "Waterfox"],
    ["zen", "󰖟", "Zen Browser"],
    ["thorium", "󰖟", "Thorium"],
    ["tor-browser", "", "Tor Browser"],
    ["floorp", "󰈹", "Floorp"],
    # Terminals
    ["gnome-terminal", "", "GNOME Terminal"],
    ["kitty", "󰄛", "Kitty Terminal"],
    ["konsole", "", "Konsole"],
    ["alacritty", "", "Alacritty"],
    ["wezterm", "", "Wezterm"],
    ["foot", "󰽒", "Foot Terminal"],
    ["tilix", "", "Tilix"],
    ["xterm", "", "XTerm"],
    ["urxvt", "", "URxvt"],
    ["st", "", "st Terminal"],
    ["com.mitchellh.ghostty", "󰊠", "Ghostty"],
    # Development Tools
    ["cursor", "󰨞", "Cursor"],
    ["vscode", "󰨞", "VS Code"],
    ["code", "󰨞", "VS Code"],
    ["sublime-text", "", "Sublime Text"],
    ["atom", "", "Atom"],
    ["android-studio", "󰀴", "Android Studio"],
    ["jetbrains-idea", "", "IntelliJ IDEA"],
    ["jetbrains-pycharm", "󱃖", "PyCharm"],
    ["jetbrains-webstorm", "󱃖", "WebStorm"],
    ["zed", "󱃖", "Zed"],
    ["jetbrains-phpstorm", "󱃖", "PhpStorm"],
    ["Postman", "󱃖", "Postman"],
    ["eclipse", "", "Eclipse"],
    ["netbeans", "", "NetBeans"],
    ["docker", "", "Docker"],
    ["vim", "", "Vim"],
    ["neovim", "", "Neovim"],
    ["neovide", "", "Neovide"],
    ["emacs", "", "Emacs"],
    # Communication Tools
    ["slack", "󰒱", "Slack"],
    ["telegram-desktop", "", "Telegram"],
    ["org.telegram.desktop", "", "Telegram"],
    ["whatsapp", "󰖣", "WhatsApp"],
    ["teams", "󰊻", "Microsoft Teams"],
    ["skype", "󰒯", "Skype"],
    ["thunderbird", "", "Thunderbird"],
    # File Managers
    ["nautilus", "󰝰", "Files (Nautilus)"],
    ["thunar", "󰝰", "Thunar"],
    ["pcmanfm", "󰝰", "PCManFM"],
    ["nemo", "󰝰", "Nemo"],
    ["ranger", "󰝰", "Ranger"],
    ["doublecmd", "󰝰", "Double Commander"],
    ["krusader", "󰝰", "Krusader"],
    # Media Players
    ["vlc", "󰕼", "VLC Media Player"],
    ["mpv", "", "MPV"],
    ["rhythmbox", "󰓃", "Rhythmbox"],
    # Graphics Tools
    ["gimp", "", "GIMP"],
    ["inkscape", "", "Inkscape"],
    ["krita", "", "Krita"],
    ["blender", "󰂫", "Blender"],
    # Video Editing
    ["kdenlive", "", "Kdenlive"],
    # Games and Gaming Platforms
    ["lutris", "󰺵", "Lutris"],
    ["heroic", "󰺵", "Heroic Games Launcher"],
    ["minecraft", "󰍳", "Minecraft"],
    ["csgo", "󰺵", "CS:GO"],
    ["dota2", "󰺵", "Dota 2"],
    # Office and Productivity
    ["evernote", "", "Evernote"],
    ["sioyek", "", "Sioyek"],
    # Cloud Services and Sync
    ["dropbox", "󰇣", "Dropbox"],
    # cleanup and maintenance tools
    ["org.bleachbit.bleachbit", "", "BleachBit"],
    ["stacer", "", "Stacer"],
    # Desktop
    ["^$", "󰇄", "Desktop"],
]

# Other constants
NOTIFICATION_WIDTH = 400
NOTIFICATION_IMAGE_SIZE = 64
NOTIFICATION_ACTION_NUMBER = 3
HIGH_POLL_INTERVAL = 3600  # 1 hour in seconds


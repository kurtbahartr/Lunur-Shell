from gi.repository import Gtk, GLib
from fabric.utils import exec_shell_command, exec_shell_command_async
from shared import ButtonWidget
from utils.icons import icons
from utils.widget_utils import get_icon
from utils.config import widget_config
from utils import ExecutableNotFoundError
import utils.functions as helpers
from shared.dbus_helper import GioDBusHelper

power_profiles = ["balanced", "performance", "power-saver"]

class PowerProfileButton(ButtonWidget):
    def __init__(self, widget_config: dict, **kwargs):
        super().__init__(
            config=widget_config["power_profiles"],
            name="power-profile-button",
            **kwargs,
        )

        if not helpers.executable_exists("powerprofilesctl"):
            raise ExecutableNotFoundError("powerprofilesctl")

        self.icon_widget = None
        self.current_profile = None

        self.update_profile_display()
        self.connect("clicked", self.on_click)
        self.init_dbus_listener()

    def get_current_profile(self):
        try:
            profile = exec_shell_command("powerprofilesctl get").strip()
            if profile not in power_profiles:
                return "balanced"
            return profile
        except Exception:
            return "balanced"

    def update_profile_display(self):
        profile = self.get_current_profile()
        if profile == self.current_profile:
            return

        self.current_profile = profile
        icon_name = icons.get("powerprofiles", {}).get(profile, "dialog-question-symbolic")
        new_icon = get_icon(icon_name, size=self.config.get("icon_size", 20))

        if self.icon_widget:
            self.box.remove(self.icon_widget)

        self.icon_widget = new_icon
        self.box.add(self.icon_widget)
        self.icon_widget.show()

        self.set_tooltip_text(f"Power Profile: {profile.capitalize()}")
        self.box.show_all()

    def on_click(self, button):
        next_profile = self.get_next_profile()
        self.set_power_profile(next_profile)

    def get_next_profile(self):
        if self.current_profile not in power_profiles:
            return power_profiles[0]
        idx = power_profiles.index(self.current_profile)
        return power_profiles[(idx + 1) % len(power_profiles)]

    def set_power_profile(self, profile):
        if profile not in power_profiles:
            return
        try:
            exec_shell_command_async(f"powerprofilesctl set {profile}")
        except Exception:
            pass

    def init_dbus_listener(self):
        def on_properties_changed(connection, sender_name, object_path, interface_name, signal_name, parameters):
            iface, changed_props, _ = parameters.unpack()
            if "ActiveProfile" in changed_props:
                self.update_profile_display()

        dbus = GioDBusHelper(
            bus_name="net.hadess.PowerProfiles",
            object_path="/net/hadess/PowerProfiles",
            interface_name="net.hadess.PowerProfiles",
        )
        dbus.listen_signal(
            sender="net.hadess.PowerProfiles",
            interface_name="org.freedesktop.DBus.Properties",
            member="PropertiesChanged",
            object_path="/net/hadess/PowerProfiles",
            callback=on_properties_changed,
        )

from gi.repository import GLib
from fabric.utils import exec_shell_command_async
from shared.widget_container import ButtonWidget
from utils.icons import icons
from utils.widget_utils import get_icon
from utils.exceptions import ExecutableNotFoundError
import utils.functions as helpers
from shared.dbus_helper import GioDBusHelper

# Power profile options
power_profiles = ["balanced", "performance", "power-saver"]


class PowerProfileButton(ButtonWidget):
    _profile_icons = {}

    def __init__(self, widget_config: dict, **kwargs):
        super().__init__(
            config=widget_config["power_profiles"],
            name="power-profile-button",
            **kwargs,
        )

        if not helpers.executable_exists("powerprofilesctl"):
            raise ExecutableNotFoundError("powerprofilesctl")

        # Initialize with a default profile
        self.current_profile = "balanced"
        self.icon_widget = None

        # Helper to hold the DBus connection so it isn't garbage collected
        self.dbus_helper = None

        # Cache icons if not already
        if not PowerProfileButton._profile_icons:
            for profile in power_profiles:
                PowerProfileButton._profile_icons[profile] = get_icon(
                    icons.get("powerprofiles", {}).get(
                        profile, "dialog-question-symbolic"
                    ),
                    size=self.config.get("icon_size", 20),
                )

        # Set initial icon
        self.icon_widget = PowerProfileButton._profile_icons[self.current_profile]
        self.box.add(self.icon_widget)
        self.icon_widget.show()
        self.set_tooltip_text(f"Power Profile: {self.current_profile.capitalize()}")
        self.box.show_all()

        # Update actual profile asynchronously
        GLib.idle_add(self.update_profile_display)

        # Connect click and DBus listener
        self.connect("clicked", self.on_click)
        self.init_dbus_listener()

    def get_current_profile(self, callback):
        """Fetch current profile asynchronously and call callback(profile)"""

        def inner(output):
            if output:
                profile = output.strip()
                if profile in power_profiles:
                    callback(profile)
                    return
            # Fallback if output is empty or invalid
            callback("balanced")

        exec_shell_command_async("powerprofilesctl get", inner)

    def update_profile_display(self):
        """Update widget display asynchronously"""

        def apply_profile(profile):
            # Even if profile is same, we might want to ensure icon is correct
            self.current_profile = profile

            if self.icon_widget:
                self.box.remove(self.icon_widget)

            self.icon_widget = PowerProfileButton._profile_icons.get(profile)
            self.box.add(self.icon_widget)
            self.icon_widget.show()
            self.set_tooltip_text(f"Power Profile: {profile.capitalize()}")
            self.box.show_all()

        self.get_current_profile(apply_profile)

    def on_click(self, button):
        next_profile = self.get_next_profile()
        # Optimistically update the variable locally so the UI feels responsive
        self.current_profile = next_profile
        self.set_power_profile(next_profile)

    def get_next_profile(self):
        idx = (
            power_profiles.index(self.current_profile)
            if self.current_profile in power_profiles
            else 0
        )
        return power_profiles[(idx + 1) % len(power_profiles)]

    def set_power_profile(self, profile):
        if profile not in power_profiles:
            return

        # Define a callback to force an update once the command finishes
        def on_set_finished(output):
            self.update_profile_display()

        try:
            # Pass the callback to exec_shell_command_async
            exec_shell_command_async(f"powerprofilesctl set {profile}", on_set_finished)
        except Exception:
            pass

    def init_dbus_listener(self):
        """Listen for DBus signals from powerprofiles daemon"""

        def on_properties_changed(
            connection,
            sender_name,
            object_path,
            interface_name,
            signal_name,
            parameters,
        ):
            iface, changed_props, _ = parameters.unpack()
            if "ActiveProfile" in changed_props:
                GLib.idle_add(self.update_profile_display)

        # FIX: Assign to self.dbus_helper so it isn't Garbage Collected
        self.dbus_helper = GioDBusHelper(
            bus_name="net.hadess.PowerProfiles",
            object_path="/net/hadess/PowerProfiles",
            interface_name="net.hadess.PowerProfiles",
        )

        self.dbus_helper.listen_signal(
            sender="net.hadess.PowerProfiles",
            interface_name="org.freedesktop.DBus.Properties",
            member="PropertiesChanged",
            object_path="/net/hadess/PowerProfiles",
            callback=on_properties_changed,
        )

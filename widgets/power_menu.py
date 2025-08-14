from gi.repository import GLib
from shared.widget_container import ButtonWidget
from utils.icons import icons
from utils.widget_utils import get_icon
from utils import BarConfig
from fabric.utils import exec_shell_command_async
import getpass


class PowerWidget(ButtonWidget):
    """Base class for power menu widgets with optional label and tooltip."""

    def __init__(self, name, icon_key, widget_config=None, command=None, **kwargs):
        if widget_config is None:
            widget_config = BarConfig()

        config = widget_config.get(name, widget_config)
        super().__init__(config=config, name=name, **kwargs)

        icon_name = icons["powermenu"][icon_key]
        self.icon_widget = get_icon(icon_name, size=config.get("icon_size", 16))
        self.box.add(self.icon_widget)
        self.icon_widget.show()
        self.box.show_all()

        label_text = config.get("label")
        if label_text:
            self.set_label(label_text)

        tooltip_text = config.get("tooltip")
        if tooltip_text:
            self.set_tooltip_text(tooltip_text)

        self.command = command
        if self.command:
            self.connect("button-press-event", self.on_click)

    def on_click(self, *_):
        if self.command:
            exec_shell_command_async(self.command)
        return True  # Stop further propagation


class SleepWidget(PowerWidget):
    def __init__(self, widget_config=None, **kwargs):
        super().__init__(
            "sleep",
            "sleep",
            widget_config,
            command="systemctl suspend",
            **kwargs,
        )


class RebootWidget(PowerWidget):
    def __init__(self, widget_config=None, **kwargs):
        super().__init__(
            "reboot",
            "reboot",
            widget_config,
            command="systemctl reboot",
            **kwargs,
        )


class LogoutWidget(PowerWidget):
    def __init__(self, widget_config=None, **kwargs):
        user = getpass.getuser()
        command = f"loginctl terminate-user {user}"
        super().__init__(
            "logout",
            "logout",
            widget_config,
            command=command,
            **kwargs,
        )


class ShutdownWidget(PowerWidget):
    def __init__(self, widget_config=None, **kwargs):
        super().__init__(
            "shutdown",
            "shutdown",
            widget_config,
            command="systemctl poweroff",
            **kwargs,
        )


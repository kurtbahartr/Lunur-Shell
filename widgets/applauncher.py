from fabric.widgets.button import Button
from modules.launcher import AppLauncher
from utils.functions import get_distro_icon
from utils.widget_utils import text_icon
from utils.config import widget_config

app_launcher = widget_config["app_launcher"]
icon_size = app_launcher["icon_size"]
app_icon_size = app_launcher["app_icon_size"]

# Pass app_icon_size to launcher instance on creation
launcher = AppLauncher(app_icon_size=app_icon_size)
launcher.show_all()
launcher.hide()

class AppLauncherButton(Button):
    def __init__(self):
        super().__init__(
            name="arch-button",
            child=text_icon(get_distro_icon(), {"size": icon_size}),
        )
        self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args):
        if launcher.is_visible():
            launcher.hide()
        else:
            launcher.show_all()

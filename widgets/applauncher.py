from fabric.widgets.button import Button
from modules.launcher import AppLauncher
from utils.functions import get_distro_icon
from utils.widget_utils import text_icon
from utils.config import widget_config
from utils import BarConfig
from shared import ButtonWidget


app_launcher = widget_config["app_launcher"]
icon_size = app_launcher["icon_size"]
app_icon_size = app_launcher["app_icon_size"]

launcher = AppLauncher(app_icon_size=app_icon_size)
launcher.show_all()
launcher.hide()


class AppLauncherButton(ButtonWidget):
    def __init__(self, widget_config: BarConfig, **kwargs):
        self.icon_widget = text_icon(get_distro_icon(), {"size": icon_size})

        super().__init__(
            config=widget_config["app_launcher"],
            name="app-launcher-button",
            child=self.icon_widget,
            **kwargs,
        )

        self.box.children = (self.icon_widget,)
        self.icon_widget.show_all()

        self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args):
        if launcher.is_visible():
            launcher.hide()
        else:
            launcher.show_all()

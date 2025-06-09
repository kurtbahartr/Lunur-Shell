from fabric.widgets.button import Button
from modules.launcher import AppLauncher
from utils.functions import get_distro_icon

launcher = AppLauncher()
launcher.show_all()
launcher.hide()


class AppLauncherButton(Button):
    def __init__(self):
        super().__init__(
            name="arch-button",
            label=get_distro_icon(),
            style="font-family: 'Nerd Font', monospace; font-size: 18px; padding: 4px 8px;",
        )
        self.connect("clicked", self.on_clicked)

    def on_clicked(self, *args):
        if launcher.is_visible():
            launcher.hide() 
        else:
            launcher.show_all() 

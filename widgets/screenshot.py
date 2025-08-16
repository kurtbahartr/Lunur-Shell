from gi.repository import Gtk, Gdk
from fabric.widgets.label import Label
from shared import ButtonWidget
from utils.widget_utils import nerd_font_icon
from services.screen_record import ScreenRecorderService
from utils.config import widget_config

class ScreenShotWidget(ButtonWidget):
    """A widget to switch themes."""

    def __init__(self, **kwargs):
        super().__init__(config=widget_config["screenshot"], name="screenshot", **kwargs)

        self.initialized = False

        self.recorder_service = None

        self.box.children = nerd_font_icon(
            icon=self.config.get("icon"),
            props={"style_classes": "panel-font-icon"},
        )

        if self.config.get("label"):
            self.box.add(Label(label=" screenshot", style_classes="panel-text"))

        if self.config.get("tooltip"):
            self.set_tooltip_text("Screen Shot")

        self.connect("clicked", self.handle_click)

    def lazy_init(self, *_):
        if not self.initialized:
            self.recorder_service = ScreenRecorderService()
            self.initialized = True

    def handle_click(self, *_):
        """Start recording the screen."""
        self.lazy_init()

        if not self.initialized:
            return  # Early exit if script not available

        self.recorder_service.screenshot(
            config=self.config,
        )

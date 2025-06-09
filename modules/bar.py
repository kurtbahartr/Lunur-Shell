from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from utils.widget_utils import lazy_load_widget 

# Widget registry for lazy loading
widget_registry = {
    "AppLauncherButton": "widgets.applauncher.AppLauncherButton",
    "WorkspacesWidget": "widgets.workspaces.WorkspacesWidget",
    "DateTimeWidget": "widgets.datetime_menu.DateTimeWidget",
}

class StatusBar(Window):
    def __init__(self):
        super().__init__(
            name="status-bar",
            layer="top",
            anchor="left top right",
            margin="6px 6px 0px 6px",
            exclusivity="auto",
            visible=False,
            all_visible=False,
        )

        self.connect("key-press-event", self.on_key_press)

        # Lazy load each widget
        widgets = {
            name: lazy_load_widget(name, widget_registry)() for name in widget_registry
        }

        start_container = Box(
            name="bar-start",
            spacing=4,
            orientation="h",
            children=[
                widgets["AppLauncherButton"],
                widgets["WorkspacesWidget"],
            ],
        )

        center_container = Box(
            name="bar-center",
            spacing=4,
            orientation="h",
            children=[
                widgets["DateTimeWidget"],
            ],
        )

        end_container = Box(
            name="bar-end",
            spacing=4,
            orientation="h",
            children=[],
        )

        self.children = CenterBox(
            name="bar-inner",
            start_children=start_container,
            center_children=center_container,
            end_children=end_container,
        )

        self.show_all()

    def on_key_press(self, widget, event):
        if event.keyval == 65307:  # Escape key
            self.hide()
            return True
        return False

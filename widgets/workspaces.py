from fabric.widgets.box import Box
from fabric.hyprland.widgets import Workspaces, WorkspaceButton


class WorkspacesWidget(Box):
    def __init__(self):
        super().__init__(
            name="workspaces-container",
            spacing=4,
            orientation="h",
            children=Workspaces(
                name="workspaces",
                spacing=4,
                buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=None),
            ),
        )


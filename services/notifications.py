from typing import Set, cast
from gi.repository import GdkPixbuf

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.image import Image
from fabric.widgets.wayland import WaylandWindow
from fabric.notifications import Notifications, Notification
from fabric.utils import invoke_repeater

from utils.constants import (
    NOTIFICATION_WIDTH,
    NOTIFICATION_IMAGE_SIZE,
    NOTIFICATION_ACTION_NUMBER,
)

class NotificationWidget(Box):
    def __init__(self, notification: Notification, auto_dismiss: bool, timeout: int):
        super().__init__(
            size=(NOTIFICATION_WIDTH, -1),
            name="notification",
            spacing=8,
            orientation="h",
        )

        self._notification = notification

        # Main content box expands horizontally and vertically in this widget
        content_box = Box(spacing=8, orientation="h", expand=True)
        self.add(content_box)

        # Optional image
        if (pixbuf := self._notification.image_pixbuf):
            scaled = pixbuf.scale_simple(
                NOTIFICATION_IMAGE_SIZE,
                NOTIFICATION_IMAGE_SIZE,
                GdkPixbuf.InterpType.BILINEAR,
            )
            content_box.add(Image(pixbuf=scaled))

        # Text container expands horizontally
        text_box = Box(orientation="v", spacing=2, expand=True)
        content_box.add(text_box)

        # Summary text
        summary_label = Label(self._notification.summary, name="summary")
        text_box.add(summary_label)

        # Body text if present
        if self._notification.body:
            body_label = Label(self._notification.body, name="body")
            text_box.add(body_label)

        # Action buttons if any, added below main content box
        actions = self._notification.actions or []
        if actions:
            actions_box = Box(orientation="h", spacing=4)
            for action in actions[:NOTIFICATION_ACTION_NUMBER]:
                button = Button(label=action)
                button.connect("clicked", lambda _, a=action: notification.activate_action(a))
                actions_box.add(button)
            # Add actions box below main content (full width)
            self.add(actions_box)

        # Auto-dismiss logic
        if auto_dismiss:
            invoke_repeater(
                timeout,
                lambda: self._notification.close("expired"),
                initial_call=False,
            )

        # Clean up when closed
        self._notification.connect(
            "closed",
            lambda *_: (
                self.get_parent().remove(self) if self.get_parent() else None,
                self.destroy(),
            ),
        )

class NotificationPopup(WaylandWindow):
    def __init__(self, config):
        notif_cfg = config.get("notification", {})

        anchor = notif_cfg.get("anchor", "top-right")
        auto_dismiss = notif_cfg.get("auto_dismiss", True)
        ignored: Set[str] = set(notif_cfg.get("ignored", []))
        timeout = notif_cfg.get("timeout", 3000)
        max_count = notif_cfg.get("max_count", 5)

        super().__init__(
            name="notifications",
            size=(NOTIFICATION_WIDTH, -1),
            spacing=8,
            anchor=anchor,
            margin="8px",
            visible=True,
            all_visible=True,
        )

        self._container = Box(
            size=2,
            spacing=8,
            orientation="v",
            name="notifications-container",
            expand=True,
        )
        self.add(self._container)

        self._auto_dismiss = auto_dismiss
        self._ignored = ignored
        self._timeout = timeout
        self._max_count = max_count

        Notifications(on_notification_added=self._on_notification_added)

    def _on_notification_added(self, service, nid):
        notification = cast(Notification, service.get_notification_from_id(nid))
        if notification.summary in self._ignored:
            return

        children = self._container.get_children()
        if len(children) >= self._max_count:
            oldest = children[0]
            self._container.remove(oldest)
            oldest.destroy()

        widget = NotificationWidget(
            notification,
            auto_dismiss=self._auto_dismiss,
            timeout=self._timeout,
        )

        # Set expand properties on the widget
        widget.hexpand = True
        widget.vexpand = True

        self._container.add(widget)


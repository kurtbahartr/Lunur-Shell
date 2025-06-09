from typing import cast
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.widgets.wayland import WaylandWindow
from fabric.notifications import Notifications, Notification
from fabric.utils import invoke_repeater
from gi.repository import GdkPixbuf

from utils.constants import NOTIFICATION_WIDTH, NOTIFICATION_IMAGE_SIZE, NOTIFICATION_ACTION_NUMBER

NOTIFICATION_TIMEOUT = 10 * 1000  # 10 seconds


class NotificationWidget(Box):
    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            size=(NOTIFICATION_WIDTH, -1),
            name="notification",
            spacing=8,
            orientation="v",
            **kwargs,
        )

        self._notification = notification

        body_container = Box(spacing=4, orientation="h")

        if image_pixbuf := self._notification.image_pixbuf:
            body_container.add(
                Image(
                    pixbuf=image_pixbuf.scale_simple(
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        GdkPixbuf.InterpType.BILINEAR,
                    )
                )
            )

        body_container.add(
            Box(
                spacing=4,
                orientation="v",
                children=[
                    Box(
                        orientation="h",
                        children=[
                            Label(
                                label=self._notification.summary,
                                ellipsization="middle",
                            )
                            .build()
                            .add_style_class("summary")
                            .unwrap(),
                        ],
                        h_expand=True,
                        v_expand=True,
                    )
                    .build(
                        lambda box, _: box.pack_end(
                            Button(
                                image=Image(
                                    icon_name="close-symbolic",
                                    icon_size=18,
                                ),
                                v_align="center",
                                h_align="end",
                                on_clicked=lambda *_: self._notification.close(),
                            ),
                            False,
                            False,
                            0,
                        )
                    ),
                    Label(
                        label=self._notification.body,
                        line_wrap="word-char",
                        v_align="start",
                        h_align="start",
                    )
                    .build()
                    .add_style_class("body")
                    .unwrap(),
                ],
                h_expand=True,
                v_expand=True,
            )
        )

        self.add(body_container)

        if actions := self._notification.actions:
            self.add(
                Box(
                    spacing=4,
                    orientation="h",
                    children=[
                        Button(
                            h_expand=True,
                            v_expand=True,
                            label=action.label,
                            on_clicked=lambda *_, action=action: action.invoke(),
                        )
                        for action in actions[:NOTIFICATION_ACTION_NUMBER]  # Respect max actions
                    ],
                )
            )

        self._notification.connect(
            "closed",
            lambda *_: (
                parent.remove(self) if (parent := self.get_parent()) else None,
                self.destroy(),
            ),
        )

        invoke_repeater(
            NOTIFICATION_TIMEOUT,
            lambda: self._notification.close("expired"),
            initial_call=False,
        )


def create_notification_window() -> WaylandWindow:
    container = Box(
        size=2,
        spacing=4,
        orientation="v",
        name="notifications-container",
    )

    window = WaylandWindow(
        name="notifications",
        anchor="top right",
        margin="8px",
        visible=True,
        all_visible=True,
        child=container,
    )

    Notifications(
        on_notification_added=lambda service, nid: container.add(
            NotificationWidget(
                cast(Notification, service.get_notification_from_id(nid))
            )
        )
    )

    return window

import os
import gi
from gi.repository import GdkPixbuf, GLib, Gtk
from fabric.widgets.revealer import Revealer

gi.require_versions({"Gtk": "3.0", "GdkPixbuf": "2.0"})


def resolve_icon(item, icon_size: int = 16):
    default_theme = Gtk.IconTheme.get_default()

    pixmap = getattr(item, "icon_pixmap", None)
    if pixmap:
        try:
            return pixmap.as_pixbuf(icon_size, "bilinear")
        except Exception:
            pass

    icon_name = getattr(item, "icon_name", None)
    if icon_name and os.path.isfile(icon_name):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(
                icon_name, icon_size, icon_size
            )
        except GLib.Error:
            pass

    icon_theme_path = getattr(item, "icon_theme_path", None)
    if icon_theme_path and icon_name:
        theme = Gtk.IconTheme.new()
        theme.prepend_search_path(icon_theme_path)
        try:
            return theme.load_icon(
                os.path.basename(icon_name), icon_size, Gtk.IconLookupFlags.FORCE_SIZE
            )
        except GLib.Error:
            pass

    if icon_name:
        try:
            return default_theme.load_icon(
                os.path.basename(icon_name), icon_size, Gtk.IconLookupFlags.FORCE_SIZE
            )
        except GLib.Error:
            if os.path.isfile(icon_name):
                try:
                    return GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_name, icon_size, icon_size
                    )
                except GLib.Error:
                    pass

    try:
        return default_theme.load_icon(
            "image-missing", icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )
    except GLib.Error:
        return None


def create_slide_revealer(
    child,
    slide_direction: str = "left",
    transition_duration: int = 250,
    initially_revealed: bool = False,
) -> Revealer:
    if slide_direction not in ("left", "right"):
        raise ValueError(
            f"Invalid 'slide_direction'. Expected 'left' or 'right', got '{slide_direction}'"
        )

    gtk_direction = "slide_left" if slide_direction == "left" else "slide_right"

    return Revealer(
        child=child,
        transition_type=gtk_direction,
        transition_duration=transition_duration,
        reveal_child=initially_revealed,
    )


def set_expanded(
    revealer, toggle_icon, slide_direction: str, icon_size: int, expanded: bool
):
    revealer.set_reveal_child(expanded)

    if slide_direction == "left":
        arrow_icon = "left" if not expanded else "right"
    else:
        arrow_icon = "left" if expanded else "right"

    if toggle_icon is None:
        return

    from utils.icons import icons

    try:
        toggle_icon.set_from_icon_name(icons["ui"]["arrow"][arrow_icon], icon_size)
    except Exception:
        pass


def on_leave(
    widget, event, revealer, slide_direction: str, toggle_icon, icon_size: int
):
    alloc = revealer.get_allocation()
    x, y = widget.translate_coordinates(revealer, int(event.x), int(event.y))
    if not (0 <= x <= alloc.width and 0 <= y <= alloc.height):
        set_expanded(revealer, toggle_icon, slide_direction, icon_size, expanded=False)

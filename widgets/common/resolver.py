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

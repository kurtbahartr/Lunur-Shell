import os
import gi
from gi.repository import GdkPixbuf, GLib, Gtk

gi.require_versions({"Gtk": "3.0", "GdkPixbuf": "2.0"})


def resolve_icon(item, icon_size: int = 16):
    if not item:
        return None

    icon_name = getattr(item, "icon_name", None)
    icon_theme_path = getattr(item, "icon_theme_path", None)

    if pixmap := getattr(item, "icon_pixmap", None):
        try:
            return pixmap.as_pixbuf(icon_size, "bilinear")
        except Exception:
            pass

    if not icon_name:
        return _get_missing_icon(icon_size)

    if os.path.isfile(icon_name):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(
                icon_name, icon_size, icon_size
            )
        except GLib.Error:
            pass

    icon_base = os.path.basename(icon_name)

    if icon_theme_path:
        theme = Gtk.IconTheme.new()
        theme.prepend_search_path(icon_theme_path)
        # Removed: set_custom_theme (Too risky/unnecessary)
        try:
            return theme.load_icon(icon_base, icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
        except GLib.Error:
            pass

    try:
        default_theme = Gtk.IconTheme.get_default()
        return default_theme.load_icon(
            icon_base, icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )
    except GLib.Error:
        pass

    return _get_missing_icon(icon_size)


def _get_missing_icon(size: int):
    try:
        theme = Gtk.IconTheme.get_default()
        return theme.load_icon("image-missing", size, Gtk.IconLookupFlags.FORCE_SIZE)
    except GLib.Error:
        return None

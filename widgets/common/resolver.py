import os
import gi
from gi.repository import GdkPixbuf, GLib, Gtk

gi.require_versions({"Gtk": "3.0", "GdkPixbuf": "2.0"})


def resolve_icon(item, icon_size: int = 16):
    if not item:
        return None

    icon_name = getattr(item, "icon_name", None)

    if not icon_name:
        return None

    icon_base = os.path.basename(icon_name)
    try:
        default_theme = Gtk.IconTheme.get_default()
        return default_theme.load_icon(
            icon_base, icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )
    except GLib.Error:
        pass

    if os.path.isfile(icon_name):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_size(
                icon_name, icon_size, icon_size
            )
        except GLib.Error:
            pass

    return None

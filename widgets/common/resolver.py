import os
import gi
from gi.repository import Gdk, GdkPixbuf, GLib, Gray, Gtk
from fabric.widgets.image import Image
from fabric.widgets.revealer import Revealer

def resolve_icon(item, icon_size: int = 16):
    try:
        # Attempt to get pixmap from Gray
        pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), icon_size)
        if pixmap:
            return pixmap.as_pixbuf(icon_size, GdkPixbuf.InterpType.HYPER)

        # Try icon name with custom theme path
        icon_name = item.get_icon_name()
        icon_theme_path = item.get_icon_theme_path()

        if icon_theme_path:
            theme = Gtk.IconTheme.new()
            theme.prepend_search_path(icon_theme_path)
            try:
                return theme.load_icon(icon_name, icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
            except GLib.Error:
                pass

        # Try loading from file path
        if os.path.exists(icon_name):
            return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, icon_size, icon_size)

        # Fallback to default icon theme
        return Gtk.IconTheme.get_default().load_icon(icon_name, icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
    except Exception:
        # Ultimate fallback: 'image-missing' icon
        return Gtk.IconTheme.get_default().load_icon(
            "image-missing", icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )

def create_slide_revealer(
    child,
    slide_direction: str = "left", 
    transition_duration: int = 250, 
    initially_revealed: bool = False
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

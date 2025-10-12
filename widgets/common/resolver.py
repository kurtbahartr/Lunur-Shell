import os
import gi
from gi.repository import Gdk, GdkPixbuf, GLib, Gray, Gtk
from fabric.widgets.image import Image
from fabric.widgets.revealer import Revealer


def resolve_icon(item, icon_size: int = 16):
    try:
        # First, try to get the icon name and path
        icon_name = item.icon_name  # Direct property access
        icon_theme_path = item.icon_theme_path  # Direct property access

        # If a full path is provided, try to load directly from file
        if icon_name and os.path.isfile(icon_name):
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_size(
                    icon_name, icon_size, icon_size
                )
            except GLib.Error:
                pass

        # If icon theme path is provided, create a custom icon theme
        if icon_theme_path:
            theme = Gtk.IconTheme.new()
            theme.prepend_search_path(icon_theme_path)

            try:
                # Try loading with custom theme
                return theme.load_icon(
                    os.path.basename(icon_name),
                    icon_size,
                    Gtk.IconLookupFlags.FORCE_SIZE,
                )
            except GLib.Error:
                pass

        # Try system default icon theme
        default_theme = Gtk.IconTheme.get_default()

        try:
            # Try loading from default theme
            return default_theme.load_icon(
                os.path.basename(icon_name), icon_size, Gtk.IconLookupFlags.FORCE_SIZE
            )
        except GLib.Error:
            # If still not found, try loading from full path
            if icon_name and os.path.isfile(icon_name):
                try:
                    return GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_name, icon_size, icon_size
                    )
                except GLib.Error:
                    pass

        # Absolute last resort: use a generic icon
        return default_theme.load_icon(
            "image-missing", icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )

    except Exception as e:
        print(f"Icon resolution error: {e}")
        # Ultimate fallback
        return Gtk.IconTheme.get_default().load_icon(
            "image-missing", icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )


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

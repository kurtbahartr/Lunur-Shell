# widgets/quick_settings/sliders/slider_row.py

from fabric.widgets.box import Box
from fabric.widgets.scale import Scale
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from gi.repository import Gtk, Pango


class SliderRow(Box):
    """A reusable slider row with icon, slider, and optional percentage label."""

    def __init__(
        self,
        icon_name: str,
        min_value: float = 0,
        max_value: float = 100,
        initial_value: float = 50,
        on_change: callable = None,
        show_percentage: bool = True,
        style_class: str = "slider-row",
        **kwargs,
    ):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            style_classes=[style_class],
            **kwargs,
        )

        self._on_change = on_change
        self._updating = False  # Prevent feedback loops

        # Icon
        self.icon = Image(style_classes="slider-icon")
        self.icon.set_from_icon_name(icon_name, 20)
        self.pack_start(self.icon, False, False, 0)

        # Scale/Slider
        self.scale = Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            min_value=min_value,
            max_value=max_value,
            value=initial_value,
            draw_value=False,
            h_expand=True,
            style_classes="qs-slider",
        )
        self.scale.connect("value-changed", self._on_value_changed)
        self.pack_start(self.scale, True, True, 0)

        # Percentage label
        self.percentage_label = None
        if show_percentage:
            self.percentage_label = Label(
                label=f"{int(initial_value)}%",
                style_classes="slider-percentage",
            )
            self.percentage_label.set_size_request(45, -1)

            # Force bold using Pango
            font_desc = Pango.FontDescription("Sans Bold 10")  # adjust size if needed
            self.percentage_label.modify_font(font_desc)

            self.pack_start(self.percentage_label, False, False, 0)

    def _on_value_changed(self, scale):
        if self._updating:
            return

        value = scale.get_value()

        if self.percentage_label:
            self.percentage_label.set_label(f"{int(value)}%")

        if self._on_change:
            self._on_change(value)

    def set_value(self, value: float):
        """Set slider value without triggering the change callback."""
        self._updating = True
        self.scale.set_value(value)
        if self.percentage_label:
            self.percentage_label.set_label(f"{int(value)}%")
        self._updating = False

    def set_icon(self, icon_name: str):
        """Update the slider icon."""
        self.icon.set_from_icon_name(icon_name, 20)

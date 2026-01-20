import textwrap
import shutil
from typing import Iterator, Tuple
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.utils import get_desktop_applications
from gi.repository import GdkPixbuf, GLib
from utils.config import widget_config
from shared.scrolled_view import ScrolledView
import utils.functions as helpers
import re
import subprocess
from fabric.utils import logger
import math


class Calculator:
    """Handles all calculator and conversion operations"""

    def __init__(self):
        # Weight conversion factors to grams (base unit)
        self.weight_to_grams = {
            "mg": 0.001,
            "g": 1,
            "kg": 1000,
            "mt": 1000000,  # metric ton
            "ton": 1000000,  # metric ton (default)
            "tonne": 1000000,  # metric ton
            "t": 1000000,  # metric ton
            "lb": 453.592,
            "lbs": 453.592,
            "pound": 453.592,
            "pounds": 453.592,
            "ust": 907185,  # US ton (short ton)
        }

        # Liquid conversion factors to milliliters (base unit)
        self.liquid_to_ml = {
            "ml": 1,
            "l": 1000,
            "liter": 1000,
            "liters": 1000,
            "floz": 29.5735,  # US fluid ounce
            "oz": 29.5735,  # fluid ounce
            "cup": 236.588,  # US cup
            "cups": 236.588,
            "pint": 473.176,  # US pint
            "pints": 473.176,
            "quart": 946.353,  # US quart
            "quarts": 946.353,
            "gal": 3785.41,  # US gallon
            "gallon": 3785.41,
            "gallons": 3785.41,
        }

    def calculate(self, query: str):
        """Try to evaluate a math expression or conversion safely

        Prioritizes:
        1. Unit Conversions
        2. Accounting percentages (100 + 20% -> 120)
        3. Standard Math with Order of Operations (2 + 3 * 4 -> 14)
        """
        if not query or not query.strip():
            return None

        # 1. Check for specific Unit Conversions
        temp_result = self._try_temperature_conversion(query)
        if temp_result is not None:
            return temp_result, "🌡️ Temperature"

        weight_result = self._try_weight_conversion(query)
        if weight_result is not None:
            return weight_result, "⚖️ Weight"

        liquid_result = self._try_liquid_conversion(query)
        if liquid_result is not None:
            return liquid_result, "🥤 Volume"

        # 2. Check for "Accounting" Percentage calculations
        # Standard math says 100 + 10% is 100 + 0.1 = 100.1
        # But humans often mean 100 + (10% of 100) = 110.
        # We catch this specific pattern here.
        match = re.match(r"^(\d+\.?\d*)\s*([+\-])\s*(\d+\.?\d*)%$", query)
        if match:
            base = float(match.group(1))
            op = match.group(2)
            perc = float(match.group(3))

            value = base * (perc / 100)
            if op == "+":
                result = base + value
            else:  # op == "-"
                result = base - value
            return f"{result:.2f}", "📊 Percentage"

        # Check for "what is X% of Y" pattern
        match = re.match(r"^(\d+\.?\d*)%\s*(?:of|\*)\s*(\d+\.?\d*)$", query)
        if match:
            perc, base = float(match.group(1)), float(match.group(2))
            result = base * (perc / 100)
            return f"{result:.2f}", "📊 Percentage"

        # 3. Universal Math Evaluation (Respects Order of Operations)
        # This handles: 2+3*4, 5^2, sqrt(16), 50 * 5% (as 0.05)
        return self._try_math_expression(query)

    def _try_math_expression(self, query: str):
        """Evaluates standard math expressions respecting PEMDAS/BODMAS."""

        if not re.match(r"^[\d+\-*/().^% a-z,]+$", query.lower()):
            return None

        if not re.search(r"[+\-*/^%a-z]", query.lower()):
            return None

        safe_query = query.replace("^", "**")

        safe_query = re.sub(r"(\d+\.?\d*)%", r"(\1/100)", safe_query)

        safe_dict = {
            "__builtins__": {},
            "sqrt": math.sqrt,
            "pow": pow,
            "abs": abs,
            "round": round,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "pi": math.pi,
            "e": math.e,
            "ceil": math.ceil,
            "floor": math.floor,
        }

        try:
            result = eval(safe_query, safe_dict, {})

            # Format the result
            if isinstance(result, (int, float)):
                if isinstance(result, float) and result.is_integer():
                    return int(result), "🧮 Math"
                return round(result, 10), "🧮 Math"
            return result, "🧮 Math"

        except Exception:
            return None

    def _try_temperature_conversion(self, query: str):
        """Try to convert temperature units"""
        query = query.strip().lower()

        # Pattern 1: Simple conversion (e.g., "100c", "212f", "100°c")
        match = re.match(r"^(-?\d+\.?\d*)°?([cf])$", query)
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            if unit == "c":
                result = (value * 9 / 5) + 32
                return f"{result:.2f}°F"
            else:
                result = (value - 32) * 5 / 9
                return f"{result:.2f}°C"

        # Pattern 2: Explicit conversion
        match = re.match(r"^(-?\d+\.?\d*)°?([cf])\s+(?:to|in)\s+°?([cf])$", query)
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            if from_unit == to_unit:
                return f"{value}°{to_unit.upper()}"

            if from_unit == "c":
                result = (value * 9 / 5) + 32
                return f"{result:.2f}°F"
            else:
                result = (value - 32) * 5 / 9
                return f"{result:.2f}°C"

        return None

    def _try_weight_conversion(self, query: str):
        """Try to convert weight units"""
        query = query.strip().lower()
        units_regex = "mg|g|kg|mt|ton|tonne|t|lb|lbs|pound|pounds|ust"

        # Pattern 1: Simple weight
        match = re.match(rf"^(\d+\.?\d*)\s*({units_regex})s?$", query)
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            grams = value * self.weight_to_grams[unit]

            if unit in ["mg", "g", "kg", "mt", "ton", "tonne", "t"]:
                result = grams / self.weight_to_grams["lb"]
                return f"{result:.2f} lbs"
            else:
                result = grams / self.weight_to_grams["kg"]
                return f"{result:.2f} kg"

        # Pattern 2: Explicit conversion
        match = re.match(
            rf"^(\d+\.?\d*)\s*({units_regex})s?\s+(?:to|in)\s+({units_regex})s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            if from_unit == "pounds":
                from_unit = "lb"
            if to_unit == "pounds":
                to_unit = "lb"

            if from_unit == to_unit:
                return f"{value} {to_unit}"

            grams = value * self.weight_to_grams[from_unit]
            result = grams / self.weight_to_grams[to_unit]

            if result >= 1000 or result < 0.01:
                return f"{result:.2e} {to_unit}"
            elif result < 1:
                return f"{result:.4f} {to_unit}"
            else:
                return f"{result:.2f} {to_unit}"

        return None

    def _try_liquid_conversion(self, query: str):
        """Try to convert liquid volume units"""
        query = query.strip().lower()
        units_regex = "ml|l|liter|liters|floz|oz|cup|cups|pint|pints|quart|quarts|gal|gallon|gallons"

        # Pattern 1: Simple liquid volume
        match = re.match(rf"^(\d+\.?\d*)\s*({units_regex})s?$", query)
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            ml = value * self.liquid_to_ml[unit]

            if unit in ["ml", "l", "liter", "liters"]:
                result = ml / self.liquid_to_ml["floz"]
                return f"{result:.2f} fl oz"
            else:
                if ml >= 1000:
                    result = ml / self.liquid_to_ml["l"]
                    return f"{result:.2f} l"
                else:
                    return f"{ml:.2f} ml"

        # Pattern 2: Explicit conversion
        match = re.match(
            rf"^(\d+\.?\d*)\s*({units_regex})s?\s+(?:to|in)\s+({units_regex})s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            if from_unit.endswith("s") and from_unit not in [
                "lbs",
                "cups",
            ]:  # Basic naive plural check
                pass  # Detailed normalization is handled in regex grouping usually, but being safe

            if from_unit == to_unit:
                return f"{value} {to_unit}"

            ml = value * self.liquid_to_ml.get(from_unit, 1)  # .get for safety
            ml = value * self.liquid_to_ml[from_unit]
            result = ml / self.liquid_to_ml[to_unit]

            if result >= 1000 or result < 0.01:
                return f"{result:.2e} {to_unit}"
            elif result < 1:
                return f"{result:.4f} {to_unit}"
            else:
                return f"{result:.2f} {to_unit}"

        return None


class AppLauncher(ScrolledView):
    def __init__(self, **kwargs):
        config = widget_config["app_launcher"]
        self.app_icon_size = config["app_icon_size"]
        self.show_descriptions = config["show_descriptions"]

        # Pre-allocate list
        self._all_apps: list = []
        self.calculator = Calculator()

        super().__init__(
            name="app-launcher",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            arrange_func=self._arrange_items,
            add_item_func=self._create_item_widget,
            placeholder="Search Applications...",
            min_content_size=(280, 320),
            max_content_size=(560, 320),
            **kwargs,
        )

    def _arrange_items(self, query: str) -> Iterator:
        """Filter items based on query. Optimized for speed."""

        if any(c.isdigit() for c in query):
            calc_result = self.calculator.calculate(query)
            if calc_result is not None:
                yield ("calc", *calc_result)

        query_cf = query.casefold()

        for app in self._all_apps:
            # _search_string is pre-computed. No string concatenation here!
            if query_cf in app._search_string:
                yield app

    def _create_item_widget(self, item) -> Button:
        """Creates the UI row for a search result."""

        if isinstance(item, tuple) and item[0] == "calc":
            return self._build_calc_row(item)

        app = item

        pixbuf = app.get_icon_pixbuf()
        if pixbuf:
            pixbuf = pixbuf.scale_simple(
                self.app_icon_size,
                self.app_icon_size,
                GdkPixbuf.InterpType.BILINEAR,
            )

        labels_box = Box(orientation="v", spacing=2, v_align="center")

        labels_box.add(
            Label(
                label=app.display_name or "Unknown",
                h_align="start",
                v_align="start",
                style="font-weight: bold;",  # Optional styling
            )
        )

        if self.show_descriptions and app.description:
            wrapped_desc = textwrap.fill(app.description, width=60)
            labels_box.add(
                Label(
                    label=wrapped_desc,
                    h_align="start",
                    v_align="start",
                    style="font-size: 0.85em; opacity: 0.7;",
                )
            )

        content_box = Box(
            orientation="h",
            spacing=12,
            children=[
                Image(pixbuf=pixbuf, h_align="start", size=self.app_icon_size),
                labels_box,
            ],
        )

        return Button(
            child=content_box,
            tooltip_text=app.description if self.show_descriptions else None,
            on_clicked=lambda *_: (app.launch(), self.hide()),
        )

    def _build_calc_row(self, item: Tuple) -> Button:
        """Helper to build calculator UI row."""
        _, result, calc_type = item

        content_box = Box(
            orientation="h",
            spacing=12,
            children=[
                Label(
                    label="🔢",
                    h_align="start",
                    v_align="center",
                    style="font-size: 20px;",
                ),
                Box(
                    orientation="v",
                    spacing=2,
                    v_align="center",
                    h_expand=True,
                    children=[
                        Label(
                            label=f"= {result}",
                            h_align="start",
                            v_align="start",
                            style="font-weight: bold;",
                        ),
                        Box(
                            orientation="h",
                            spacing=8,
                            h_expand=True,
                            children=[
                                Label(
                                    label="Click to copy",
                                    h_align="start",
                                    style="font-size: 0.85em; opacity: 0.7;",
                                ),
                                Label(
                                    label=str(calc_type),
                                    h_align="end",
                                    h_expand=True,
                                    style="font-size: 0.85em; opacity: 0.5;",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        return Button(
            child=content_box,
            tooltip_text=f"Copy result: {result}",
            on_clicked=lambda *_: self._copy_to_clipboard(str(result)),
        )

    def _copy_to_clipboard(self, text: str):
        """Optimized clipboard copy."""
        if not shutil.which("wl-copy"):
            logger.error("wl-copy not found. Install wl-clipboard.")
            return

        def copy_task():
            try:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                p.communicate(input=text.encode("utf-8"))

                # Close launcher on success
                GLib.idle_add(self.hide)
            except Exception as e:
                logger.error(f"Clipboard error: {e}")

        # Run in thread to not block UI
        helpers.run_in_thread(copy_task)

    def show_all(self):
        """Refreshes app list and pre-calculates search strings."""
        apps = get_desktop_applications()

        for app in apps:
            if not self.show_descriptions:
                app.description = ""

            app._search_string = (
                f"{app.display_name or ''} {app.name} {app.generic_name or ''}"
            ).casefold()

        self._all_apps = apps
        super().show_all()

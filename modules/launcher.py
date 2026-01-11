from typing import Iterator
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.box import Box
from fabric.utils import get_desktop_applications, DesktopApp
from gi.repository import GdkPixbuf, GLib
from utils.config import widget_config
from shared.scrolled_view import ScrolledView
import utils.functions as helpers
import re
import subprocess
import shlex
from loguru import logger
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

        Returns a tuple of (result, calculator_type_label) or None if no match
        """
        if not query or not query.strip():
            return None

        # Check for temperature conversions
        temp_result = self._try_temperature_conversion(query)
        if temp_result is not None:
            return temp_result, "🌡️ Temperature"

        # Check for weight conversions
        weight_result = self._try_weight_conversion(query)
        if weight_result is not None:
            return weight_result, "⚖️ Weight"

        # Check for liquid conversions
        liquid_result = self._try_liquid_conversion(query)
        if liquid_result is not None:
            return liquid_result, "🥤 Volume"

        # Check for percentage calculations (e.g., "250 + 15%", "80 - 20%", "2 * 20%", "2 / 20%")
        match = re.match(r"^(\d+\.?\d*)\s*([+\-*/])\s*(\d+\.?\d*)%$", query)
        if match:
            base, op, perc = (
                float(match.group(1)),
                match.group(2),
                float(match.group(3)),
            )
            value = base * (perc / 100)
            if op == "+":
                result = base + value
            elif op == "-":
                result = base - value
            elif op == "*":
                result = base * (perc / 100)
            else:  # op == "/"
                result = base / (perc / 100)
            return f"{result:.2f}", "📊 Percentage"

        # Check for "what is X% of Y" pattern (e.g., "15% of 200", "20% * 500")
        match = re.match(r"^(\d+\.?\d*)%\s*(?:of|\*)\s*(\d+\.?\d*)$", query)
        if match:
            perc, base = float(match.group(1)), float(match.group(2))
            result = base * (perc / 100)
            return f"{result:.2f}", "📊 Percentage"

        # Check for simple percentage conversion (e.g., "15%" -> "0.15")
        match = re.match(r"^(\d+\.?\d*)%$", query)
        if match:
            perc = float(match.group(1))
            return f"{perc / 100:.4f}", "📊 Percentage"

        # Check for math functions (sqrt, abs, pow, etc.)
        if re.match(r"^[\d+\-*/().^ a-z,]+$", query.lower()):
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
            }

            query_normalized = query.replace("^", "**")

            try:
                result = eval(query_normalized, safe_dict, {})

                # Format the result nicely
                if isinstance(result, float):
                    # Remove unnecessary decimals
                    if result.is_integer():
                        return int(result), "🧮 Math"
                    return round(result, 10), "🧮 Math"
                return result, "🧮 Math"
            except:
                pass  # Try next pattern

        # Check for power operations (e.g., "2^8", "5**3")
        if re.match(r"^[\d+\-*/().^ ]+$", query):
            query_normalized = query.replace("^", "**")

            # Must contain at least one operator
            if re.search(r"[+\-*/^]", query):
                try:
                    result = eval(query_normalized, {"__builtins__": {}}, {})

                    # Format the result nicely
                    if isinstance(result, float):
                        if result.is_integer():
                            return int(result), "🧮 Math"
                        return round(result, 10), "🧮 Math"
                    return result, "🧮 Math"
                except:
                    return None

        # Only allow numbers, operators, parentheses, and whitespace
        if not re.match(r"^[\d+\-*/(). ]+$", query):
            return None

        # Must contain at least one operator
        if not re.search(r"[+\-*/]", query):
            return None

        try:
            # Safely evaluate the expression
            result = eval(query, {"__builtins__": {}}, {})
            # Format the result nicely
            if isinstance(result, float):
                # Remove unnecessary decimals
                if result.is_integer():
                    return int(result), "🧮 Math"
                return round(result, 10), "🧮 Math"
            return result, "🧮 Math"
        except:
            return None

    def _try_temperature_conversion(self, query: str):
        """Try to convert temperature units

        Supported formats:
        - 100c, 100C, 100°c, 100°C -> Celsius to Fahrenheit
        - 212f, 212F, 212°f, 212°F -> Fahrenheit to Celsius
        - 100c to f, 100°C to °F -> Explicit conversion
        - 212f to c, 212°F to °C -> Explicit conversion
        """
        query = query.strip().lower()

        # Pattern 1: Simple conversion (e.g., "100c", "212f", "100°c")
        match = re.match(r"^(-?\d+\.?\d*)°?([cf])$", query)
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            if unit == "c":
                # Celsius to Fahrenheit
                result = (value * 9 / 5) + 32
                return f"{result:.2f}°F"
            else:  # unit == "f"
                # Fahrenheit to Celsius
                result = (value - 32) * 5 / 9
                return f"{result:.2f}°C"

        # Pattern 2: Explicit conversion (e.g., "100c to f", "212°F to °C")
        match = re.match(r"^(-?\d+\.?\d*)°?([cf])\s+(?:to|in)\s+°?([cf])$", query)
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            # If converting to same unit, just return the value
            if from_unit == to_unit:
                return f"{value}°{to_unit.upper()}"

            if from_unit == "c":
                # Celsius to Fahrenheit
                result = (value * 9 / 5) + 32
                return f"{result:.2f}°F"
            else:  # from_unit == "f"
                # Fahrenheit to Celsius
                result = (value - 32) * 5 / 9
                return f"{result:.2f}°C"

        return None

    def _try_weight_conversion(self, query: str):
        """Try to convert weight units

        Supported formats:
        - Metric: kg, g, mg, mt/ton/tonne (metric ton)
        - Imperial/US: lb/lbs/pound/pounds, ust (US ton)

        Examples:
        - 100kg, 100 kg -> converts to lbs
        - 150lbs to kg, 150 pounds to kg
        - 5kg to g, 5000g to kg
        - 1mt to ust, 1 metric ton to us ton
        """
        query = query.strip().lower()

        # Pattern 1: Simple weight (e.g., "100kg", "150 lbs")
        match = re.match(
            r"^(\d+\.?\d*)\s*(mg|g|kg|mt|ton|tonne|t|lb|lbs|pound|pounds|ust)s?$", query
        )
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            # Convert to grams first
            grams = value * self.weight_to_grams[unit]

            # Decide what to convert to based on the input unit
            if unit in ["mg", "g", "kg", "mt", "ton", "tonne", "t"]:
                # Metric to Imperial (pounds)
                result = grams / self.weight_to_grams["lb"]
                return f"{result:.2f} lbs"
            else:
                # Imperial to Metric (kilograms)
                result = grams / self.weight_to_grams["kg"]
                return f"{result:.2f} kg"

        # Pattern 2: Explicit conversion (e.g., "100kg to lbs", "150 pounds to kg")
        match = re.match(
            r"^(\d+\.?\d*)\s*(mg|g|kg|mt|ton|tonne|t|lb|lbs|pound|pounds|ust)s?\s+(?:to|in)\s+(mg|g|kg|mt|ton|tonne|t|lb|lbs|pound|pounds|ust)s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            # Normalize plurals
            if from_unit == "pounds":
                from_unit = "lb"
            if to_unit == "pounds":
                to_unit = "lb"

            # If converting to same unit, just return the value
            if from_unit == to_unit:
                return f"{value} {to_unit}"

            # Convert via grams
            grams = value * self.weight_to_grams[from_unit]
            result = grams / self.weight_to_grams[to_unit]

            # Format the result
            if result >= 1000 or result < 0.01:
                return f"{result:.2e} {to_unit}"
            elif result < 1:
                return f"{result:.4f} {to_unit}"
            else:
                return f"{result:.2f} {to_unit}"

        return None

    def _try_liquid_conversion(self, query: str):
        """Try to convert liquid volume units

        Supported formats:
        - Metric: ml, l (liters)
        - Imperial/US: floz/oz (fluid ounces), cup, pint, quart, gal/gallon

        Examples:
        - 100ml -> converts to fl oz
        - 1l to gal, 1 liter to gallon
        - 16floz to ml
        - 2cup to ml
        """
        query = query.strip().lower()

        # Pattern 1: Simple liquid volume (e.g., "100ml", "16 floz")
        match = re.match(
            r"^(\d+\.?\d*)\s*(ml|l|liter|liters|floz|oz|cup|cups|pint|pints|quart|quarts|gal|gallon|gallons)s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            # Convert to ml first
            ml = value * self.liquid_to_ml[unit]

            # Decide what to convert to based on the input unit
            if unit in ["ml", "l", "liter", "liters"]:
                # Metric to Imperial (fluid ounces)
                result = ml / self.liquid_to_ml["floz"]
                return f"{result:.2f} fl oz"
            else:
                # Imperial to Metric (liters or ml)
                if ml >= 1000:
                    result = ml / self.liquid_to_ml["l"]
                    return f"{result:.2f} l"
                else:
                    return f"{ml:.2f} ml"

        # Pattern 2: Explicit conversion (e.g., "100ml to floz", "1gal to l")
        match = re.match(
            r"^(\d+\.?\d*)\s*(ml|l|liter|liters|floz|oz|cup|cups|pint|pints|quart|quarts|gal|gallon|gallons)s?\s+(?:to|in)\s+(ml|l|liter|liters|floz|oz|cup|cups|pint|pints|quart|quarts|gal|gallon|gallons)s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            # Normalize plurals
            if from_unit in ["liters", "cups", "pints", "quarts", "gallons"]:
                from_unit = from_unit[:-1]  # Remove 's'
            if to_unit in ["liters", "cups", "pints", "quarts", "gallons"]:
                to_unit = to_unit[:-1]  # Remove 's'

            # If converting to same unit, just return the value
            if from_unit == to_unit:
                return f"{value} {to_unit}"

            # Convert via ml
            ml = value * self.liquid_to_ml[from_unit]
            result = ml / self.liquid_to_ml[to_unit]

            # Format the result
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
        self._all_apps: list[DesktopApp] = []
        self.calculator = Calculator()

        def arrange_func(query: str) -> Iterator:
            # Check if query is a math expression
            calc_result = self.calculator.calculate(query)
            if calc_result is not None:
                result, calc_type = calc_result
                # Return calculator result as first item with type indicator
                yield ("calc", result, calc_type)

            # Then show matching apps
            query_cf = query.casefold()
            for app in self._all_apps:
                if (
                    query_cf
                    in f"{app.display_name or ''} {app.name} {app.generic_name or ''}".casefold()
                ):
                    yield app

        def add_item_func(item) -> Button:
            # Handle calculator result
            if isinstance(item, tuple) and item[0] == "calc":
                _, result, calc_type = item

                content_box = Box(
                    orientation="h",
                    spacing=12,
                    children=[
                        Label(label="🔢", h_align="start", v_align="center"),
                        Box(
                            orientation="v",
                            spacing=2,
                            v_align="center",
                            h_expand=True,
                            children=[
                                # Result line
                                Label(
                                    label=f"= {result}",
                                    h_align="start",
                                    v_align="start",
                                ),
                                # "Click to copy" and calculator type on same row
                                Box(
                                    orientation="h",
                                    spacing=8,
                                    h_expand=True,
                                    children=[
                                        Label(
                                            label="Click to copy",
                                            h_align="start",
                                            v_align="start",
                                            h_expand=True,
                                            style="font-size: 0.85em; opacity: 0.7;",
                                        ),
                                        Label(
                                            label=calc_type,
                                            h_align="end",
                                            v_align="start",
                                            style="font-size: 0.85em;",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
                return Button(
                    child=content_box,
                    tooltip_text=f"Calculator result: {result}",
                    on_clicked=lambda *_: self._copy_to_clipboard(str(result)),
                )

            # Handle regular app
            app = item
            pixbuf = app.get_icon_pixbuf()
            if pixbuf:
                pixbuf = pixbuf.scale_simple(
                    self.app_icon_size,
                    self.app_icon_size,
                    GdkPixbuf.InterpType.BILINEAR,
                )

            # Labels for app name and optional description
            labels = [
                Label(
                    label=app.display_name or "Unknown",
                    h_align="start",
                    v_align="start",
                )
            ]
            if self.show_descriptions and app.description:

                def split_description(desc, max_line_length=80):
                    words = desc.split()
                    lines = []
                    current_line = []
                    for word in words:
                        if len(" ".join(current_line + [word])) <= max_line_length:
                            current_line.append(word)
                        else:
                            lines.append(" ".join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(" ".join(current_line))
                    return "\n".join(lines)

                description = split_description(app.description)

                labels.append(
                    Label(
                        label=description,
                        h_align="start",
                        v_align="start",
                    )
                )

            # Compose the button child: horizontal box with icon and vertical labels box
            content_box = Box(
                orientation="h",
                spacing=12,
                children=[
                    Image(pixbuf=pixbuf, h_align="start", size=self.app_icon_size),
                    Box(orientation="v", spacing=2, v_align="center", children=labels),
                ],
            )

            # Return the button widget
            return Button(
                child=content_box,
                tooltip_text=app.description if self.show_descriptions else None,
                on_clicked=lambda *_: (app.launch(), self.hide()),
            )

        super().__init__(
            name="app-launcher",
            layer="top",
            anchor="center",
            exclusivity="none",
            keyboard_mode="on-demand",
            visible=False,
            all_visible=False,
            arrange_func=arrange_func,
            add_item_func=add_item_func,
            placeholder="Search Applications...",
            min_content_size=(280, 320),
            max_content_size=(560, 320),
            **kwargs,
        )

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard using wl-copy"""
        try:
            helpers.check_executable_exists("wl-copy")
        except Exception as e:
            logger.error(f"wl-copy not found: {e}")
            logger.error(
                "Please install wl-clipboard package to enable clipboard functionality."
            )
            return

        def copy():
            try:
                escaped_text = shlex.quote(text)
                logger.debug(f"Copying to clipboard: {text}")
                subprocess.run(
                    f"echo -n {escaped_text} | wl-copy",
                    shell=True,
                    check=True,
                )
                GLib.idle_add(self.hide)
            except subprocess.CalledProcessError as e:
                logger.exception(f"Error copying to clipboard: {e}")
            return False

        GLib.idle_add(copy)

    def show_all(self):
        apps = get_desktop_applications()
        if not self.show_descriptions:
            # Clear descriptions if disabled in config
            for app in apps:
                app.description = ""
        self._all_apps = apps
        super().show_all()

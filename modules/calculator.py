import math
import re


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

        # Create regex strings sorted by length (descending) to prevent partial matching
        # e.g., ensure "lbs" is matched before "lb"
        self.weight_regex = "|".join(
            sorted(self.weight_to_grams.keys(), key=len, reverse=True)
        )
        self.liquid_regex = "|".join(
            sorted(self.liquid_to_ml.keys(), key=len, reverse=True)
        )

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
        return self._try_math_expression(query)

    def _try_math_expression(self, query: str):
        """Evaluates standard math expressions respecting PEMDAS/BODMAS."""
        # Lowercase everything for consistent matching (allows Sqrt, SQRT, etc.)
        query_lower = query.lower()

        # Regex explanation:
        # \d+      : digits
        # \.?\d*   : optional decimals
        # [+\-*/]  : basic operators
        # ()       : parentheses
        # .        : decimal point
        # ^        : exponent
        # %        : modulo/percent
        # a-z      : functions (sqrt, etc)
        # ,        : commas (for tuples or multi-arg functions)
        if not re.match(r"^[\d+\-*/().^% a-z,]+$", query_lower):
            return None

        # Ensure at least one operator, function, or comma exists
        # Added ',' to allow "1, 2" to evaluate to a tuple
        if not re.search(r"[+\-*/^%a-z,]", query_lower):
            return None

        safe_query = query_lower.replace("^", "**")
        # Handle "50%" as "50/100" in math context
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

        # Pattern 1: Simple weight (e.g., "1kg")
        # Note: self.weight_regex handles sorting keys by length (lbs before lb)
        match = re.match(rf"^(\d+\.?\d*)\s*({self.weight_regex})s?$", query)
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

        # Pattern 2: Explicit conversion (e.g., "1kg to lbs")
        match = re.match(
            rf"^(\d+\.?\d*)\s*({self.weight_regex})s?\s+(?:to|in)\s+({self.weight_regex})s?$",
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

            # Thresholds for scientific notation
            # Adjusted lower bound from 0.0001 to 0.01 to catch 0.001 (1mg) correctly
            if result >= 1000000 or result < 0.01:
                return f"{result:.2e} {to_unit}"
            elif result < 1:
                return f"{result:.4f} {to_unit}"
            else:
                return f"{result:.2f} {to_unit}"

        return None

    def _try_liquid_conversion(self, query: str):
        """Try to convert liquid volume units"""
        query = query.strip().lower()

        # Pattern 1: Simple liquid volume
        match = re.match(rf"^(\d+\.?\d*)\s*({self.liquid_regex})s?$", query)
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
            rf"^(\d+\.?\d*)\s*({self.liquid_regex})s?\s+(?:to|in)\s+({self.liquid_regex})s?$",
            query,
        )
        if match:
            value = float(match.group(1))
            from_unit = match.group(2)
            to_unit = match.group(3)

            if from_unit == to_unit:
                return f"{value} {to_unit}"

            # Calculate conversion
            ml = value * self.liquid_to_ml[from_unit]
            result = ml / self.liquid_to_ml[to_unit]

            # Normalize display unit
            display_unit = to_unit
            if display_unit == "floz":
                display_unit = "fl oz"

            # Thresholds for scientific notation
            # Adjusted lower bound from 0.0001 to 0.01
            if result >= 1000000 or result < 0.01:
                return f"{result:.2e} {display_unit}"
            elif result < 1:
                return f"{result:.4f} {display_unit}"
            else:
                return f"{result:.2f} {display_unit}"

        return None

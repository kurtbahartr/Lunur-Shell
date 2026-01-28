import pytest
import math
from modules.launcher import Calculator


@pytest.fixture
def calc():
    """Fixture to initialize the calculator before every test."""
    return Calculator()


# -----------------------------------------------------------------------------
# 1. Order of Operations (PEMDAS / BODMAS)
# -----------------------------------------------------------------------------
# P - Parentheses
# E - Exponents
# M/D - Multiplication/Division (Left to Right)
# A/S - Addition/Subtraction (Left to Right)


@pytest.mark.parametrize(
    "query, expected",
    [
        # Basic Precedence
        ("2 + 3 * 4", 14),  # Multiplication before Addition
        ("(2 + 3) * 4", 20),  # Parentheses first
        ("10 - 4 / 2", 8),  # Division before Subtraction
        ("10 * 4 + 2", 42),  # Multiplication before Addition
        # Left-to-Right Associativity
        ("10 - 5 - 2", 3),  # (10-5)-2 = 3, NOT 10-(5-2)=7
        ("20 / 4 * 2", 10),  # (20/4)*2 = 10, NOT 20/(4*2)=2.5
        # Exponents
        ("2 ^ 3", 8),  # Basic exponent
        ("2^3 * 4", 32),  # Exponent before Multiplication
        ("2^(3 * 2)", 64),  # Parentheses inside exponent
        ("3^2 + 4^2", 25),  # Exponents before Addition
        # Complex Nested Operations
        ("5 * (3 + 2)^2", 125),  # Parentheses -> Exponent -> Multiply
        ("10 + (8 - 2) * 3", 28),  # Parentheses -> Multiply -> Add
        ("((2 + 2) * 2) ^ 2", 64),  # Nested Parentheses
        # Negative Numbers
        ("-5 + 3", -2),
        ("-5 * -5", 25),
        ("10 + -2", 8),
    ],
)
def test_order_of_operations(calc, query, expected):
    result, category = calc.calculate(query)
    assert category == "🧮 Math"
    assert result == expected


# -----------------------------------------------------------------------------
# 2. Advanced Math Functions & Constants
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        # Functions
        ("sqrt(16)", 4),
        ("sqrt(3^2 + 4^2)", 5),  # Pythagorean triple
        ("abs(-50)", 50),
        ("floor(5.9)", 5),
        ("ceil(5.1)", 6),
        ("round(5.5)", 6),
        ("round(5.4)", 5),
        # Trigonometry (inputs are radians usually)
        ("sin(0)", 0),
        ("cos(0)", 1),
        ("tan(0)", 0),
        # Constants
        ("pi", math.pi),
        ("e", math.e),
        ("floor(pi)", 3),
        # Mixed Functions and Math
        ("sqrt(100) * 2", 20),
        ("10 + abs(-10)", 20),
        ("log(e)", 1),  # Natural log of e is 1
    ],
)
def test_math_functions(calc, query, expected):
    result, category = calc.calculate(query)
    assert category == "🧮 Math"
    if isinstance(expected, float):
        assert result == pytest.approx(expected, rel=1e-5)
    else:
        assert result == expected


# -----------------------------------------------------------------------------
# 3. Percentages (Accounting vs Math Logic)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_val, expected_cat",
    [
        # Accounting Logic (The regex matchers)
        ("100 + 10%", "110.00", "📊 Percentage"),  # 100 + (10% of 100)
        ("100 - 20%", "80.00", "📊 Percentage"),  # 100 - (20% of 100)
        ("50% of 200", "100.00", "📊 Percentage"),
        ("20% * 50", "10.00", "📊 Percentage"),
        # Standard Math Logic (Python eval fallback)
        # 50 * 10% -> 50 * 0.1 -> 5
        ("50 * 10%", 5.0, "🧮 Math"),
        # Percentage in math equations
        ("100 * 5%", 5.0, "🧮 Math"),
        ("5% + 5%", 0.1, "🧮 Math"),  # 0.05 + 0.05
    ],
)
def test_percentage_logic(calc, query, expected_val, expected_cat):
    result, category = calc.calculate(query)
    assert category == expected_cat
    if category == "🧮 Math":
        assert result == pytest.approx(expected_val)
    else:
        assert result == expected_val


# -----------------------------------------------------------------------------
# 4. Unit Conversions (Expanded)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_str",
    [
        # --- Weight ---
        # Scientific Notation Threshold Check (should NOT trigger for 1000)
        ("1kg to g", "1000.00 g"),
        ("1g to mg", "1000.00 mg"),
        # Huge number (should trigger scientific notation)
        ("1000000kg to g", "1.00e+09 g"),
        # Tiny number
        ("0.000001kg to g", "1.00e-03 g"),
        # --- Liquid ---
        ("1l to ml", "1000.00 ml"),
        ("1gallon to l", "3.79 l"),
        ("1 cup to floz", "8.00 fl oz"),
        # --- Temperature ---
        ("100C", "212.00°F"),
        ("-40c", "-40.00°F"),  # The crossing point
        ("0c", "32.00°F"),
        ("98.6f", "37.00°C"),
    ],
)
def test_conversions(calc, query, expected_str):
    result, category = calc.calculate(query)
    assert result == expected_str


# -----------------------------------------------------------------------------
# 5. Robustness, Case Sensitivity & Edge Cases
# -----------------------------------------------------------------------------


def test_case_insensitivity(calc):
    # Math functions
    res1, _ = calc.calculate("Sqrt(16)")
    assert res1 == 4
    res2, _ = calc.calculate("SQRT(16)")
    assert res2 == 4

    # Units
    res3, _ = calc.calculate("1KG to LBS")
    assert res3 == "2.20 lbs"


def test_syntax_handling(calc):
    # Spaces shouldn't matter
    assert calc.calculate("2+2")[0] == 4
    assert calc.calculate("2 + 2")[0] == 4
    assert calc.calculate("  2  +  2  ")[0] == 4


def test_error_handling(calc):
    # Division by zero
    assert calc.calculate("10 / 0") is None

    # Incomplete parenthesis
    assert calc.calculate("(10 + 2") is None
    assert calc.calculate("10 + 2)") is None

    # Nonsense text
    assert calc.calculate("hello world") is None
    assert calc.calculate("one plus two") is None

    # Safety: Dangerous globals
    assert calc.calculate("__import__('os')") is None
    assert calc.calculate("eval('1+1')") is None


def test_comma_handling(calc):
    # Python eval allows commas, effectively creating tuples.
    # The regex allows commas: r"^[\d+\-*/().^% a-z,]+$"
    # Verify behavior (Currently returns a tuple)
    result, cat = calc.calculate("1, 2")
    assert result == (1, 2)
    assert cat == "🧮 Math"

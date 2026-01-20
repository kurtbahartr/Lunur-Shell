# tests/test_functions.py
import pytest
from unittest.mock import patch

from utils.functions import (
    exclude_keys,
    unique_list,
    format_time,
    convert_to_percent,
    merge_defaults,
    parse_markup,
    truncate,
    check_executable_exists,
    executable_exists,
    validate_widgets,
    ExecutableNotFoundError,
)


def test_exclude_keys():
    d = {"a": 1, "b": 2, "c": 3}
    filtered = exclude_keys(d, ["b"])
    assert filtered == {"a": 1, "c": 3}


def test_unique_list():
    lst = [1, 2, 2, 3, 4, 4, 5]
    result = unique_list(lst)
    assert sorted(result) == [1, 2, 3, 4, 5]


def test_convert_to_percent():
    assert convert_to_percent(50, 100) == 50
    assert convert_to_percent(1, 3, is_int=False) == pytest.approx((1 / 3) * 100)
    assert convert_to_percent(0, 0) == 0


def test_format_time():
    assert format_time(0) == "0 h 00 min"
    assert format_time(59) == "0 h 00 min"
    assert format_time(60) == "0 h 01 min"
    assert format_time(3600) == "1 h 00 min"
    assert format_time(3661) == "1 h 01 min"


def test_merge_defaults():
    defaults = {"a": 1, "b": {"x": 10, "y": 20}, "list": [1, 2]}
    data = {"b": {"y": 30}, "c": 3}
    merged = merge_defaults(data, defaults)
    expected = {"a": 1, "b": {"x": 10, "y": 30}, "c": 3, "list": [1, 2]}
    assert merged == expected

    data_list = {"list": [3, 4]}
    merged_list = merge_defaults(data_list, defaults)
    assert merged_list["list"] == [3, 4]


def test_parse_markup():
    text = "Hello\nWorld"
    assert parse_markup(text) == "Hello World"
    assert parse_markup(None) == ""


def test_truncate():
    assert truncate("Hello World", 11) == "Hello World"
    assert truncate("Hello World!", 11) == "Hello Worl…"
    assert truncate(None) == ""


@patch("shutil.which")
def test_executable_exists(mock_which):
    mock_which.return_value = "/usr/bin/git"
    assert executable_exists("git") is True
    mock_which.return_value = None
    assert executable_exists("random_exe") is False


@patch("shutil.which")
def test_check_executable_exists_raises(mock_which):
    mock_which.return_value = "/bin/ls"
    try:
        check_executable_exists("ls")
    except ExecutableNotFoundError:
        pytest.fail(
            "check_executable_exists raised ExecutableNotFoundError unexpectedly"
        )

    mock_which.return_value = None
    with pytest.raises(ExecutableNotFoundError):
        check_executable_exists("missing_app")


def test_validate_widgets():
    default_config = {"clock": {}, "workspaces": {}, "tray": {}}

    valid_data = {
        "layout": {"left": ["clock", "@group:0"], "right": ["@collapsible_group:0"]},
        "module_groups": [{"widgets": ["workspaces"]}],
        "collapsible_groups": [{"widgets": ["tray"]}],
    }
    validate_widgets(valid_data, default_config)

    invalid_widget = {"layout": {"left": ["unknown_widget"]}}
    with pytest.raises(ValueError, match="Invalid widget 'unknown_widget'"):
        validate_widgets(invalid_widget, default_config)

    invalid_group = {"layout": {"left": ["@group:99"]}, "module_groups": []}
    with pytest.raises(ValueError, match="Module group index 99 out of range"):
        validate_widgets(invalid_group, default_config)

    malformed_group = {
        "layout": {"left": ["@group:0"]},
        "module_groups": [{"not_widgets": []}],
    }
    with pytest.raises(ValueError, match="must be a dict with a 'widgets' list"):
        validate_widgets(malformed_group, default_config)

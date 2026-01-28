import time
import os
import filecmp
from typing import Any, cast
from fabric import Application
from fabric.utils import (
    cooldown,
    exec_shell_command,
    get_relative_path,
    monitor_file,
    logger,
)
from gi.repository import Gtk

import utils.functions as helpers
from utils.constants import (
    APPLICATION_NAME,
    APP_CACHE_DIRECTORY,
)
from utils.exceptions import ExecutableNotFoundError
from utils.config import widget_config

# --- Configuration & Logging Setup ---
DEBUG = widget_config.get("general", {}).get("debug", False)

# Disable logs if debug is False
if not DEBUG:
    for log in [
        "fabric",
        "widgets",
        "utils",
        "utils.config",
        "modules",
        "services",
        "config",
    ]:
        logger.disable(log)

_start_time = time.perf_counter() if DEBUG else None


def compile_scss():
    if not helpers.executable_exists("sass"):
        raise ExecutableNotFoundError("sass")

    # Timing is handled by the caller via helpers.total_time
    output = exec_shell_command("sass styles/main.scss dist/main.css --no-source-map")

    if output:
        logger.error("[Main] Failed to compile SCSS!")


def setup_initial_styles(target_theme: str):
    state_file = os.path.join(APP_CACHE_DIRECTORY, "current_theme_state")
    css_output = get_relative_path("dist/main.css")
    styles_dir = get_relative_path("styles")

    # The file currently being used by main.scss
    current_active_theme_file = get_relative_path("styles/theme.scss")
    # The source file for the requested theme
    source_theme_file = get_relative_path(f"styles/themes/{target_theme}.scss")

    should_compile = False
    reason = ""

    # 1. Check if output CSS exists
    if not os.path.exists(css_output):
        should_compile = True
        reason = "Output CSS missing"

    # 2. Check if the theme name changed (State check)
    elif os.path.exists(state_file):
        with open(state_file, "r") as f:
            last_theme = f.read().strip()
        if last_theme != target_theme:
            should_compile = True
            reason = f"Theme changed ({last_theme} -> {target_theme})"
    else:
        # No state file means first run
        should_compile = True
        reason = "First run (no state file)"

    # 3. Check if the specific theme file content differs (Content check)
    if not should_compile:
        if not os.path.exists(current_active_theme_file):
            should_compile = True
            reason = "Active theme file missing"
        elif os.path.exists(source_theme_file):
            if not filecmp.cmp(
                source_theme_file, current_active_theme_file, shallow=False
            ):
                should_compile = True
                reason = "Theme content mismatch"

    # 4. Global Timestamp Check
    if not should_compile:
        output_mtime = os.path.getmtime(css_output)

        modified_files = [
            f
            for root, _, files in os.walk(styles_dir)
            for f in files
            if f.endswith(".scss")
            and os.path.getmtime(os.path.join(root, f)) > output_mtime
        ]

        if modified_files:
            should_compile = True
            reason = f"Source file modified ({modified_files[0]})"

    if should_compile:
        logger.info(f"[Main] Compiling styles. Reason: {reason}")
        helpers.copy_theme(target_theme)

        helpers.total_time("Compilation", compile_scss, debug=DEBUG, category="SCSS")

        with open(state_file, "w") as f:
            f.write(target_theme)
    else:
        logger.info(f"[Main] Theme '{target_theme}' is up to date. Skipping compile.")


@cooldown(2)
@helpers.run_in_thread
def process_and_apply_css(app: Application):
    helpers.total_time("Compilation", compile_scss, debug=DEBUG, category="SCSS")
    app.set_stylesheet_from_file(get_relative_path("dist/main.css"))
    logger.info("[Main] CSS applied")


# Screen recorder functions for fabric-cli (must be at module level)
take_screenshot = None
record_start = None
record_stop = None

if __name__ == "__main__":
    helpers.check_executable_exists("sass")
    helpers.ensure_directory(APP_CACHE_DIRECTORY)

    # Import core modules directly
    from modules.bar import StatusBar
    from modules.launcher import AppLauncher

    # Instantiate core modules using total_time
    launcher = helpers.total_time(
        "AppLauncher", AppLauncher, debug=DEBUG, category="Module"
    )

    bar = helpers.total_time(
        "StatusBar",
        lambda: StatusBar(cast(Any, widget_config)),
        debug=DEBUG,
        category="Module",
    )

    windows = [bar, launcher]

    if widget_config.get("keybinds", {}).get("enabled"):
        from modules.keybinds import KeybindsWidget

        keybinds = helpers.total_time(
            "KeybindsWidget",
            lambda: KeybindsWidget(widget_config),
            debug=DEBUG,
            category="Module",
        )
        windows.append(keybinds)

    if widget_config.get("notification", {}).get("enabled"):
        from modules.notification import NotificationPopup

        notifications = helpers.total_time(
            "NotificationPopup",
            lambda: NotificationPopup(widget_config),  # type: ignore
            debug=DEBUG,
            category="Module",
        )
        windows.append(notifications)

    if widget_config.get("general", {}).get("screen_corners", {}).get("enabled"):
        from modules.corners import ScreenCorners

        screen_corners = helpers.total_time(
            "ScreenCorners",
            lambda: ScreenCorners(widget_config),
            debug=DEBUG,
            category="Module",
        )
        windows.append(screen_corners)

    if widget_config.get("osd", {}).get("enabled"):
        from modules.osd import OSDWindow

        osd = helpers.total_time(
            "OSDWindow",
            lambda: OSDWindow(widget_config),
            debug=DEBUG,
            category="Module",
        )
        windows.append(osd)

    if widget_config.get("screen_record", {}).get("enabled", True):
        from services.screen_record import (
            ScreenRecorderService,
            take_screenshot as _take_screenshot,
            record_start as _record_start,
            record_stop as _record_stop,
        )

        screen_recorder_service = ScreenRecorderService()
        screen_recorder_service.set_widget_config(
            widget_config.get("screen_record", {})
        )

        # Expose functions for fabric-cli
        take_screenshot = _take_screenshot
        record_start = _record_start
        record_stop = _record_stop

    # Setup Icons
    icon_theme = Gtk.IconTheme.get_default()  # type: ignore
    icon_theme.append_search_path(get_relative_path("./assets/icons/svg/gtk"))

    # Smart Setup
    setup_initial_styles(widget_config["theme"]["name"])

    # Create application
    app = Application(APPLICATION_NAME, windows=windows)
    app.set_stylesheet_from_file(get_relative_path("dist/main.css"))

    # File watchers for live reload
    style_monitor = monitor_file(get_relative_path("./styles"))
    watch_matugen = monitor_file(get_relative_path("./styles/themes/matugen.scss"))

    def on_theme_change(*args):
        helpers.copy_theme(widget_config["theme"]["name"])
        process_and_apply_css(app)

    watch_matugen.connect("changed", on_theme_change)
    style_monitor.connect("changed", lambda *args: process_and_apply_css(app))

    if DEBUG and _start_time:
        total_duration = time.perf_counter() - _start_time
        if total_duration < 0.001:
            total_str = f"{total_duration * 1_000_000:.2f} μs"
        else:
            total_str = f"{total_duration * 1_000:.2f} ms"
        logger.info(f"[Timing] Total startup completed in {total_str}")

    helpers.set_process_name(APPLICATION_NAME)
    app.run()

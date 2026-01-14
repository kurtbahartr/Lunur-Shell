import time
from fabric import Application
from fabric.utils import cooldown, exec_shell_command, get_relative_path, monitor_file
from loguru import logger
from gi.repository import Gtk

import utils.functions as helpers
from utils import (
    APPLICATION_NAME,
    APP_CACHE_DIRECTORY,
    ExecutableNotFoundError,
    widget_config,
)

DEBUG = widget_config.get("general", {}).get("debug", False)
_start_time = time.perf_counter() if DEBUG else None


def time_module_load(name: str, func):
    if not DEBUG:
        return func()
    start = time.perf_counter()
    result = func()
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"[Timing] Module '{name}' loaded in {elapsed_ms:.1f} ms")
    return result


def compile_scss():
    if not helpers.executable_exists("sass"):
        raise ExecutableNotFoundError("sass")

    logger.info("[Main] Compiling SCSS")
    start = time.perf_counter() if DEBUG else None

    output = exec_shell_command("sass styles/main.scss dist/main.css --no-source-map")

    if DEBUG and start:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[Timing] SCSS compiled in {elapsed_ms:.1f} ms")

    if output:
        logger.error("[Main] Failed to compile SCSS!")


@cooldown(2)
@helpers.run_in_thread
def process_and_apply_css(app: Application):
    compile_scss()
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

    # Instantiate core modules
    launcher = time_module_load("AppLauncher", AppLauncher)
    bar = time_module_load("StatusBar", lambda: StatusBar(widget_config))

    windows = [bar, launcher]

    if widget_config.get("keybinds", {}).get("enabled"):
        from modules.keybinds import KeybindsWidget

        keybinds = time_module_load(
            "KeybindsWidget", lambda: KeybindsWidget(widget_config)
        )
        windows.append(keybinds)

    if widget_config.get("notification", {}).get("enabled"):
        from modules.notification import NotificationPopup

        notifications = time_module_load(
            "NotificationPopup", lambda: NotificationPopup(widget_config)
        )
        windows.append(notifications)

    if widget_config.get("general", {}).get("screen_corners", {}).get("enabled"):
        from modules.corners import ScreenCorners

        screen_corners = time_module_load(
            "ScreenCorners", lambda: ScreenCorners(widget_config)
        )
        windows.append(screen_corners)

    if widget_config.get("osd", {}).get("enabled"):
        from modules.osd import OSDWindow

        osd = time_module_load("OSDWindow", lambda: OSDWindow(widget_config))
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

    # Setup theme and icons BEFORE compiling SCSS
    helpers.copy_theme(widget_config["theme"]["name"])

    icon_theme = Gtk.IconTheme.get_default()
    icon_theme.append_search_path(get_relative_path("./assets/icons/svg/gtk"))

    compile_scss()

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
        total_ms = (time.perf_counter() - _start_time) * 1000
        logger.info(f"[Timing] Total startup completed in {total_ms:.1f} ms")

    helpers.set_process_name(APPLICATION_NAME)
    app.run()

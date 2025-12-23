import time
import setproctitle
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    if DEBUG:
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


def _import_module(module_info):
    """Import a module and return its class."""
    name, module_path, class_name = module_info
    module = __import__(module_path, fromlist=[class_name])
    return name, getattr(module, class_name)


def _collect_enabled_modules():
    """Determine which optional modules are enabled."""
    modules = []

    if widget_config.get("keybinds", {}).get("enabled"):
        modules.append(("KeybindsWidget", "modules.keybinds", "KeybindsWidget"))

    if widget_config.get("notification", {}).get("enabled"):
        modules.append(
            ("NotificationPopup", "modules.notification", "NotificationPopup")
        )

    if widget_config.get("general", {}).get("screen_corners", {}).get("enabled"):
        modules.append(("ScreenCorners", "modules.corners", "ScreenCorners"))

    if widget_config.get("osd", {}).get("enabled"):
        modules.append(("OSDWindow", "modules.osd", "OSDWindow"))

    return modules


def _preload_optional_modules(modules):
    """Preload optional module classes in parallel."""
    if not modules:
        return {}

    classes = {}
    with ThreadPoolExecutor(max_workers=min(4, len(modules))) as executor:
        futures = {executor.submit(_import_module, m): m[0] for m in modules}
        for future in as_completed(futures):
            try:
                name, cls = future.result()
                classes[name] = cls
            except Exception as e:
                logger.error(f"Failed to import module '{futures[future]}': {e}")
    return classes


# Screen recorder functions for fabric-cli (must be at module level)
take_screenshot = None
record_start = None
record_stop = None

if __name__ == "__main__":
    helpers.ensure_directory(APP_CACHE_DIRECTORY)

    # Start SCSS compilation and module preloading in parallel
    optional_modules = _collect_enabled_modules()

    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit SCSS compilation
        scss_future = executor.submit(compile_scss)

        # Submit optional module preloading
        preload_future = executor.submit(_preload_optional_modules, optional_modules)

        # Import core modules while SCSS compiles (these are needed first)
        from modules.bar import StatusBar
        from modules.launcher import AppLauncher

        # Wait for SCSS to complete before continuing
        scss_future.result()

        # Get preloaded module classes
        preloaded_classes = preload_future.result()

    # Load core modules
    launcher = time_module_load("AppLauncher", AppLauncher)
    bar = time_module_load("StatusBar", lambda: StatusBar(widget_config))
    windows = [bar, launcher]

    # Instantiate optional modules using preloaded classes
    if "KeybindsWidget" in preloaded_classes:
        cls = preloaded_classes["KeybindsWidget"]
        keybinds = time_module_load("KeybindsWidget", lambda: cls(widget_config))
        windows.append(keybinds)

    if "NotificationPopup" in preloaded_classes:
        cls = preloaded_classes["NotificationPopup"]
        notifications = time_module_load(
            "NotificationPopup", lambda: cls(widget_config)
        )
        windows.append(notifications)

    if "ScreenCorners" in preloaded_classes:
        cls = preloaded_classes["ScreenCorners"]
        screen_corners = time_module_load("ScreenCorners", lambda: cls(widget_config))
        windows.append(screen_corners)

    if "OSDWindow" in preloaded_classes:
        cls = preloaded_classes["OSDWindow"]
        osd = time_module_load("OSDWindow", lambda: cls(widget_config))
        windows.append(osd)

    # Screen recorder service (doesn't need to block startup)
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

    # Create application
    app = Application(APPLICATION_NAME, windows=windows)
    app.set_stylesheet_from_file(get_relative_path("dist/main.css"))

    # Setup theme and icons
    helpers.copy_theme(widget_config["theme"]["name"])

    icon_theme = Gtk.IconTheme.get_default()
    icon_theme.append_search_path(get_relative_path("./assets/icons/svg/gtk"))

    # File watchers for live reload
    style_monitor = monitor_file(get_relative_path("./styles"))
    watch_matugen = monitor_file(get_relative_path("./styles/themes/matugen.scss"))

    def on_theme_change(*args):
        helpers.copy_theme(widget_config["theme"]["name"])
        process_and_apply_css(app)

    watch_matugen.connect("changed", on_theme_change)
    style_monitor.connect("changed", lambda *args: process_and_apply_css(app))

    # Log total startup time
    if DEBUG and _start_time:
        total_ms = (time.perf_counter() - _start_time) * 1000
        logger.info(f"[Timing] Total startup completed in {total_ms:.1f} ms")

    setproctitle.setproctitle(APPLICATION_NAME)
    app.run()
